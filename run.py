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
from nour.calculation_audit import audit_calculations
from nour.resilience import (validate_fixture, isolate_audit_failures,
                             health_with_quarantines, update_last_healthy, GlobalIntegrityError)
from nour.transactions import site_transaction

ROOT = Path(__file__).resolve().parent


def _build(args, output):
    fixture = json.loads((ROOT / "data/market_snapshot.json").read_text(encoding="utf-8"))
    validate_fixture(fixture, json.loads((ROOT/'data/source_codes.json').read_text()))
    fixture = apply_status(fixture, json.loads((ROOT/'data/issuer_status.json').read_text()), args.asof)
    facts=json.loads((ROOT/"data/facts_reference.json").read_text(encoding="utf-8")).get("records",{})
    news=json.loads((ROOT/"data/news.json").read_text(encoding="utf-8"))
    report = build_report(fixture, args.asof, facts=facts, news=news.get("articles",[]))
    overview_path = ROOT/'data/market_overview.json'
    overview = json.loads(overview_path.read_text()) if overview_path.exists() else {}
    from nour.resilience import retained_market_context
    import hashlib
    cache_file=ROOT/'data/last_healthy.json'
    retained=retained_market_context(hashlib.sha256((ROOT/'data/market_snapshot.json').read_bytes()).hexdigest(),
        json.loads(cache_file.read_text()) if cache_file.exists() else {},
        json.loads((ROOT/'data/health.json').read_text()) if (ROOT/'data/health.json').exists() else {})
    if retained:
        overview={**overview,'current':retained['overview']}
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
        atomic_json(output/'volume-history.json',volume_history)
        atomic_json(output/'volume-history-check.json',report['volume_history_check'])
        (output/'historique-volumes.html').write_text(
            history_page(volume_history,report['volume_history_check']),encoding='utf-8')
    atomic_json(output/'market-reference.json',report['market_overview'].get('official_reference') or
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
    atomic_json(output/'macro.json',report['macro'])
    report["runtime"] = run_context(now, schedule=os.environ.get("NOUR_SCHEDULE", ""),
        event=os.environ.get("GITHUB_EVENT_NAME", "local"), slot=args.slot,
        started_at=os.environ.get("NOUR_STARTED_AT"), run_id=os.environ.get("GITHUB_RUN_ID", ""),
        commit=source_commit(os.environ), scheduled_for=os.environ.get("NOUR_SCHEDULED_FOR") or None)
    report['provenance'] = provenance(fixture['source_commit'], report['runtime']['commit'], ROOT/'data/market_snapshot.json')
    integrity_path=ROOT/'data/market_integrity.json'
    memory_path=ROOT/'data/error_memory.json'
    integrity=json.loads(integrity_path.read_text()) if integrity_path.exists() else {}
    if retained:
        integrity={'schema_version':1,'status':'retained_validated','publication_safe':True,
            'session':retained['proof']['session'],'last_valid_proof':retained['proof'],
            'observed_at':report['health'].get('checked_at'),'cross_source_verified':False,
            'quantities_cross_source_verified':False,'reused_last_validated_snapshot':True}
    report['cross_source_volume_audit']=visible_integrity(integrity,report)
    memory=json.loads(memory_path.read_text()) if memory_path.exists() else {}
    report['error_memory_summary']=memory_summary(memory)
    atomic_json(output/'market-integrity.json',report['cross_source_volume_audit'])
    atomic_json(output/'error-memory.json',memory)
    report['collection'] = collection_view(report['health'])
    report['runtime']['collection'] = report['collection']
    report['runtime']['provenance'] = report['provenance']
    report['runtime']['market_integrity']={k:report['cross_source_volume_audit'].get(k) for k in ('status','session','observed_at','cross_source_verified')}
    for item in report['results']:
        item['collection_conflicts'] = [c for c in report['collection']['conflicts'] if c.get('symbol') == item['symbol']]
    live_path = ROOT/"data/intraday.json"
    live = json.loads(live_path.read_text()) if live_path.exists() else None
    report["intraday"] = visible_intraday(live, now)
    for item in report["results"]:
        item["intraday_quote"] = (None if item.get('resilience',{}).get('suspended',{}).get('market')
                                  else report["intraday"]["quotes"].get(item["symbol"]))
        item['intraday_status'] = report['intraday']['status']
        item["intraday_observed_at"] = report["intraday"].get("observed_at") if item["intraday_quote"] else None
    financial_health = publication_health(report)
    isolate_audit_failures(report, financial_health, 'financial')
    financial_health = health_with_quarantines(financial_health, report, 'financial')
    if financial_health['failures']:
        raise GlobalIntegrityError('Contrat financier global invalide')
    report['financial_health'] = {
        key: financial_health[key] for key in
        ('version', 'status', 'arithmetic_checks', 'documents_certified')
    }
    calculations = audit_calculations(fixture, report)
    isolate_audit_failures(report, calculations)
    calculations = health_with_quarantines(calculations, report)
    if calculations['failures']:
        raise GlobalIntegrityError('Contrat global de calcul invalide')
    atomic_json(output/'calculation-health.json', calculations)
    report['calculation_health'] = {key: calculations[key] for key in
        ('version', 'status', 'universe', 'issuers_checked', 'arithmetic_checks', 'sources_certified')}
    final_financial = health_with_quarantines(publication_health(report),report,'financial')
    financial_health = {**final_financial, 'quarantined_failures':financial_health.get('quarantined_failures', [])}
    if final_financial['failures']:
        raise GlobalIntegrityError('Sortie financière encore incohérente après isolement')
    atomic_json(output/'financial-health.json', financial_health)
    sector_health = audit_sector_report(report)
    if sector_health['violations']:
        from nour.resilience import issue
        from nour.sector_methods import guidance
        from nour.analytics import canonical_score
        rows={r['symbol']:r for r in report['results']}
        for failure in sector_health['violations']:
            row=rows.get(failure['symbol'])
            if row is None: raise GlobalIntegrityError('Univers sectoriel incohérent')
            metric=failure.get('metric')
            if metric:
                row['fundamental'][metric]=None
                row['fundamental']['metric_availability'][metric]={'status':'blocked','reason_codes':['sector_incompatibility']}
                blocked=row['fundamental']['financial_audit']['blocked_metrics']
                if metric not in blocked:blocked.append(metric)
                row['fundamental']['financial_audit']['status']='blocked'
                issue(row,'fundamental','sector_incompatibility',failure['issue'],['fundamental.'+metric])
                row['canonical_score']=canonical_score(row,row['technical'],row['fundamental'])
            else:
                row['sector_guidance']=guidance(row['symbol'],{'sector':row.get('sector')})
                issue(row,'sector_indicators','taxonomy_mismatch',failure['issue'],['sector_guidance'])
        sector_health=audit_sector_report(report)
        if sector_health['violations']:raise GlobalIntegrityError('Taxonomie sectorielle incohérente')
    atomic_json(output/'sector-readiness.json', sector_health)
    from nour.sector_validation import audit_sector_calculations
    sector_calculations=audit_sector_calculations(report)
    if sector_calculations['failures']:
        from nour.resilience import issue
        for failure in sector_calculations['failures']:
            row=next(r for r in report['results'] if r['symbol']==failure['symbol'])
            m=row['sector_indicators']['metrics'].get(failure['metric'])
            if m is None:raise GlobalIntegrityError('Calcul de segment incohérent')
            m.update(value=None,status='unavailable')
            m['reasons'].append({'reason':failure['reason']})
            issue(row,'sector_indicators','sector_arithmetic_mismatch',failure['reason'],['sector_indicators.'+failure['metric']])
        sector_calculations['quarantined_failures']=sector_calculations['failures']
        sector_calculations['failures']=audit_sector_calculations(report)['failures']
        if sector_calculations['failures']:raise GlobalIntegrityError('Contrat de calcul sectoriel incohérent')
    atomic_json(output/'sector-calculation-health.json',sector_calculations)
    financial_health=health_with_quarantines(publication_health(report),report,'financial')
    if financial_health['failures']:raise GlobalIntegrityError('Contrat financier final invalide')
    atomic_json(output/'financial-health.json',financial_health)
    report['financial_health']={k:financial_health[k] for k in ('version','status','arithmetic_checks','documents_certified')}
    continuity_path=ROOT/'data/continuity_state.json'
    report['continuity']=json.loads(continuity_path.read_text()) if continuity_path.exists() else {'status':'not_yet_observed'}
    atomic_json(output/'continuite.json',report['continuity'])
    cache_path = ROOT/'data/last_healthy.json'
    cache = update_last_healthy(json.loads(cache_path.read_text()) if cache_path.exists() else None, report, now.isoformat())
    from nour.diagnostics import update_journal
    journal_path = ROOT/'data/anomalies.json'
    report['anomaly_journal'] = update_journal(json.loads(journal_path.read_text())
        if journal_path.exists() else None, report, now.isoformat())
    codes=json.loads((ROOT/'data/source_codes.json').read_text())
    for row in report['results']:
        row['issuer_identity']={'symbol':row['symbol'],'official_market_code':codes[row['symbol']],
            'basis':'Référentiel explicite de codes source contrôlé ; aucun ISIN déduit du nom.'}
    import tempfile, shutil
    with tempfile.TemporaryDirectory() as d:
        score_dir=Path(d)/'scores'
        if (ROOT/'data/score_archive').exists():shutil.copytree(ROOT/'data/score_archive',score_dir,dirs_exist_ok=True)
        else:score_dir.mkdir()
        report['score_archive']=archive_scores(report,score_dir,now)
        pending_scores={ROOT/'data/score_archive'/x.name:json.loads(x.read_text())
            for x in score_dir.glob('*.json') if not (ROOT/'data/score_archive'/x.name).exists()}
    briefing=create_briefing(report)
    archive = ROOT/"data/briefings"
    archive.mkdir(exist_ok=True)
    slot = report["runtime"]["slot"]
    if slot in EDITIONS:
        # Preserve all three dated editions. Intermediate/manual-auto builds do
        # not rewrite the morning, midday or closing editions.
        pending_scores[archive/f'{report["runtime"]["edition_for"]}-{EDITIONS[slot]}.json']=briefing
    editions = {}
    for key, slug in EDITIONS.items():
        candidates = sorted(archive.glob(f"????-??-??-{slug}.json"))
        if candidates:
            editions[key] = json.loads(candidates[-1].read_text())
    if slot in EDITIONS: editions[slot]=briefing
    links = [{"label": b["title"], "date": b["runtime"]["edition_for"],
              "url": f"briefing-{EDITIONS[key]}.html"} for key,b in editions.items()]
    briefing["edition_links"] = links
    briefing['text_url'] = 'briefing.txt'
    (output/'briefing.txt').write_text(briefing_text(briefing),encoding='utf-8')
    for key,b in editions.items():
        b["edition_links"] = links
        if b.get('editorial_version'):
            b['text_url'] = f'briefing-{EDITIONS[key]}.txt'
            (output/b['text_url']).write_text(briefing_text(b),encoding='utf-8')
        atomic_json(output/f"briefing-{EDITIONS[key]}.json", b)
    atomic_json(output/"runtime.json", {**report["runtime"], "market":report["health"],
                "last_closed_session":briefing["market_session"],
                "intraday_status":report["intraday"]["status"], "briefings":links,
                "publication_stage":"built_before_pages_deployment"})
    target = output / "report.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (output/"news.json").write_text(json.dumps(news,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (output/"briefing.json").write_text(json.dumps(briefing,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
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
    (output/'cloture.txt').write_text(briefing_text(closing),encoding='utf-8')
    atomic_json(output/'cloture.json', closing)
    build_site(fixture, report, output, briefing=briefing, editions=editions, closing=closing)
    from tools.audit_site import audit as audit_site
    audit_site(output)
    from tools.audit_market_integrity import audit_market_integrity
    if audit_market_integrity(report)['failures']:
        raise GlobalIntegrityError('Contrôle global du marché refusé ; ancien site conservé')
    from nour.diagnostics import resolve_global_controls
    from nour.site import write_diagnostics
    resolve_global_controls(report['anomaly_journal'],now.isoformat(),report['runtime']['commit'])
    write_diagnostics(report,output)
    atomic_json(output/'report.json',report)
    return {**pending_scores,cache_path:cache,journal_path:report['anomaly_journal']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asof", default=datetime.now(ZONE).date().isoformat(), help="Analysis date YYYY-MM-DD")
    parser.add_argument("--slot", default="auto", choices=["auto", "morning", "midday", "closing", "refresh", "preclose"])
    parser.add_argument("--serve", action="store_true", help="Launch local dashboard")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    try:
        with site_transaction(ROOT/'web') as output:
            pending=_build(args, output)
    except Exception as exc:
        from nour.diagnostics import global_failure
        path=ROOT/'data/anomalies.json'
        global_failure(path,datetime.now(ZONE).isoformat(),type(exc).__name__,str(exc))
        raise
    for path,payload in pending.items():atomic_json(path,payload)
    print('Nouvelle génération complète échangée atomiquement.')
    if args.serve:
        class LocalHandler(SimpleHTTPRequestHandler):
            def __init__(self, *handler_args, **kwargs):
                super().__init__(*handler_args, directory=str(ROOT / "web"), **kwargs)

        with ThreadingHTTPServer(("127.0.0.1", args.port), LocalHandler) as server:
            print(f"Ouvrir http://127.0.0.1:{args.port}/ (Ctrl+C pour arrêter)")
            server.serve_forever()


if __name__ == "__main__":
    main()
