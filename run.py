"""Build the complete static research site and optionally serve it locally."""
import argparse
import json
import os
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from nour.engine import build_report
from nour.issuer_status import apply_status
from nour.market_integrity import visible_integrity, memory_summary
from nour.market_reference import apply_market_reference
from nour.volume_history import checked_history, compare_current, history_page
from nour.site import build_site
from nour.briefing import create_briefing
from nour.market import atomic_json
from nour.runtime import EDITIONS, ZONE, run_context, visible_intraday, source_commit
from nour.market_view import closing_summary
from nour.briefing_view import briefing_text
from nour.report_contracts import synchronize_market
from nour.macro import context_view
from nour.research import enrich, archive_scores
from tools.audit_readiness import publication_health
from nour.sector_audit import audit_sector_report
from nour.publication import collection_view, provenance

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asof", default=datetime.now(ZONE).date().isoformat(), help="Analysis date YYYY-MM-DD")
    parser.add_argument("--slot", default="auto", choices=["auto", "morning", "midday", "closing", "refresh", "preclose"])
    parser.add_argument("--serve", action="store_true", help="Launch local dashboard")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    fixture = json.loads((ROOT / "data/market_snapshot.json").read_text(encoding="utf-8"))
    fixture = apply_status(fixture, json.loads((ROOT/'data/issuer_status.json').read_text()), args.asof)
    facts=json.loads((ROOT/"data/facts_reference.json").read_text(encoding="utf-8")).get("records",{})
    news=json.loads((ROOT/"data/news.json").read_text(encoding="utf-8"))
    report = build_report(fixture, args.asof, facts=facts, news=news.get("articles",[]))
    overview_path = ROOT/'data/market_overview.json'
    overview = json.loads(overview_path.read_text()) if overview_path.exists() else {}
    reference_path=ROOT/'data/market_reference.json'
    reference=json.loads(reference_path.read_text()) if reference_path.exists() else {}
    for key in ('current','last_closed'):
        if key in overview:
            overview[key]=apply_market_reference(overview[key],reference)
    synchronize_market(report, overview.get('current', {}))
    volume_history_path=ROOT/'data/volume_history.json'
    if volume_history_path.exists():
        volume_history=checked_history(json.loads(volume_history_path.read_text()))
        report['volume_history']={**volume_history,'records':[
            row for row in volume_history['records'] if row['session']<=args.asof]}
        # A documentary comparison never changes source counters or candles.
        report['volume_history_check']=compare_current(volume_history,report['market_overview'])
        atomic_json(ROOT/'web/volume-history.json',volume_history)
        atomic_json(ROOT/'web/volume-history-check.json',report['volume_history_check'])
        (ROOT/'web/historique-volumes.html').write_text(
            history_page(volume_history,report['volume_history_check']),encoding='utf-8')
    atomic_json(ROOT/'web/market-reference.json',report['market_overview'].get('official_reference') or
                {'status':'not_available','asof':report['market_overview'].get('asof')})
    history_path = ROOT/'data/masi_history.json'
    report['masi_history'] = json.loads(history_path.read_text()).get('seances', {}) if history_path.exists() else {}
    report['masi_history'] = {d: v for d,v in report['masi_history'].items() if d <= args.asof}
    enrich(report, fixture)
    overview_health = ROOT/'data/overview_health.json'
    report['overview_health'] = json.loads(overview_health.read_text()) if overview_health.exists() else {}
    news_health = ROOT/'data/news_health.json'
    report['news_health'] = json.loads(news_health.read_text()) if news_health.exists() else {'status':'not_observed'}
    official_health = ROOT/'data/official_sources_health.json'
    report['official_sources_health'] = (json.loads(official_health.read_text())
                                        if official_health.exists() else {'status': 'not_observed'})
    health_file=ROOT/"data/health.json"
    report["health"] = json.loads(health_file.read_text()) if health_file.exists() else {
        "result":"not_configured","message":"Collecte automatique non encore exécutée"}
    now = datetime.now(ZONE)
    macro_path=ROOT/'data/macro.json'
    report['macro_source']=json.loads(macro_path.read_text()) if macro_path.exists() else {}
    report['macro']=context_view(report['macro_source'], min(now,
        datetime.fromisoformat(args.asof+'T23:59:59').replace(tzinfo=ZONE)))
    atomic_json(ROOT/'web/macro.json',report['macro'])
    report["runtime"] = run_context(now, schedule=os.environ.get("NOUR_SCHEDULE", ""),
        event=os.environ.get("GITHUB_EVENT_NAME", "local"), slot=args.slot,
        started_at=os.environ.get("NOUR_STARTED_AT"), run_id=os.environ.get("GITHUB_RUN_ID", ""),
        commit=source_commit(os.environ))
    report['provenance'] = provenance(fixture['source_commit'], report['runtime']['commit'], ROOT/'data/market_snapshot.json')
    integrity_path=ROOT/'data/market_integrity.json'
    memory_path=ROOT/'data/error_memory.json'
    report['cross_source_volume_audit']=visible_integrity(json.loads(integrity_path.read_text()) if integrity_path.exists() else {},report)
    memory=json.loads(memory_path.read_text()) if memory_path.exists() else {}
    report['error_memory_summary']=memory_summary(memory)
    atomic_json(ROOT/'web/market-integrity.json',report['cross_source_volume_audit'])
    atomic_json(ROOT/'web/error-memory.json',memory)
    report['collection'] = collection_view(report['health'])
    report['runtime']['collection'] = report['collection']
    report['runtime']['provenance'] = report['provenance']
    report['runtime']['market_integrity']={k:report['cross_source_volume_audit'].get(k) for k in ('status','session','observed_at','cross_source_verified')}
    for item in report['results']:
        item['collection_conflicts'] = [c for c in report['collection']['conflicts'] if c.get('symbol') == item['symbol']]
    report['score_archive'] = archive_scores(report, ROOT/'data/score_archive', now)
    live_path = ROOT/"data/intraday.json"
    live = json.loads(live_path.read_text()) if live_path.exists() else None
    report["intraday"] = visible_intraday(live, now)
    for item in report["results"]:
        item["intraday_quote"] = report["intraday"]["quotes"].get(item["symbol"])
        item['intraday_status'] = report['intraday']['status']
        item["intraday_observed_at"] = report["intraday"].get("observed_at") if item["intraday_quote"] else None
    briefing=create_briefing(report)
    archive = ROOT/"data/briefings"
    archive.mkdir(exist_ok=True)
    slot = report["runtime"]["slot"]
    if slot in EDITIONS:
        # Preserve all three dated editions. Intermediate/manual-auto builds do
        # not rewrite the morning, midday or closing editions.
        atomic_json(archive/f'{report["runtime"]["edition_for"]}-{EDITIONS[slot]}.json', briefing)
    editions = {}
    for key, slug in EDITIONS.items():
        candidates = sorted(archive.glob(f"????-??-??-{slug}.json"))
        if candidates:
            editions[key] = json.loads(candidates[-1].read_text())
    links = [{"label": b["title"], "date": b["runtime"]["edition_for"],
              "url": f"briefing-{EDITIONS[key]}.html"} for key,b in editions.items()]
    briefing["edition_links"] = links
    briefing['text_url'] = 'briefing.txt'
    (ROOT/'web/briefing.txt').write_text(briefing_text(briefing),encoding='utf-8')
    for key,b in editions.items():
        b["edition_links"] = links
        if b.get('editorial_version'):
            b['text_url'] = f'briefing-{EDITIONS[key]}.txt'
            (ROOT/'web'/b['text_url']).write_text(briefing_text(b),encoding='utf-8')
        atomic_json(ROOT/f"web/briefing-{EDITIONS[key]}.json", b)
    atomic_json(ROOT/"web/runtime.json", {**report["runtime"], "market":report["health"],
                "last_closed_session":briefing["market_session"],
                "intraday_status":report["intraday"]["status"], "briefings":links,
                "publication_stage":"built_before_pages_deployment"})
    target = ROOT / "web/report.json"
    financial_health = publication_health(report)
    if financial_health['failures']:
        raise ValueError('Publication refusée : incohérence arithmétique des fondamentaux : '
                         + json.dumps(financial_health['failures'], ensure_ascii=False))
    report['financial_health'] = {
        key: financial_health[key] for key in
        ('version', 'status', 'arithmetic_checks', 'documents_certified')
    }
    atomic_json(ROOT/'web/financial-health.json', financial_health)
    sector_health = audit_sector_report(report)
    if sector_health['violations']:
        raise ValueError('Publication refusée : incompatibilité sectorielle : '
                         + json.dumps(sector_health['violations'], ensure_ascii=False))
    atomic_json(ROOT/'web/sector-readiness.json', sector_health)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ROOT/"web/news.json").write_text(json.dumps(news,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (ROOT/"web/briefing.json").write_text(json.dumps(briefing,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    # Reproducible latest closing digest, separate from the scheduled editions.
    # Never label an intraday observation or today's preparation as a new close.
    closed = overview.get('last_closed', {})
    closing_report = synchronize_market({**report, 'runtime': {}, 'intraday': {}}, closed)
    closing = create_briefing(closing_report, closing_only=True)
    closing.update(title='Briefing de clôture', runtime={}, intraday={},
                   market_session=closed.get('asof'), index=closed.get('masi'),
                   market_summary=closing_summary(closed), market_status='closed' if closed else 'unavailable',
                   edition_notice='Synthèse préparée à partir de la dernière clôture datée disponible ; les fiches techniques conservent leur propre date.',
                   edition_status='closed' if closed else 'unavailable')
    closing['focus'] = [f for f in closing['focus'] if f['asof'] == closed.get('asof')]
    for f in closing['focus']:
        f.pop('intraday_quote', None)
    closing['text_url'] = 'cloture.txt'
    (ROOT/'web/cloture.txt').write_text(briefing_text(closing),encoding='utf-8')
    atomic_json(ROOT/'web/cloture.json', closing)
    build_site(fixture, report, ROOT / 'web', briefing=briefing, editions=editions, closing=closing)
    print(f"Site Nour : {len(report['results'])} titres, date {args.asof} → {ROOT / 'web/index.html'}")
    if args.serve:
        class LocalHandler(SimpleHTTPRequestHandler):
            def __init__(self, *handler_args, **kwargs):
                super().__init__(*handler_args, directory=str(ROOT / "web"), **kwargs)

        with ThreadingHTTPServer(("127.0.0.1", args.port), LocalHandler) as server:
            print(f"Ouvrir http://127.0.0.1:{args.port}/ (Ctrl+C pour arrêter)")
            server.serve_forever()


if __name__ == "__main__":
    main()
