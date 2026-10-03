"""Build the complete static research site and optionally serve it locally."""
import argparse
import json
import os
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from nour.engine import build_report
from nour.site import build_site
from nour.briefing import create_briefing
from nour.market import atomic_json
from nour.runtime import EDITIONS, ZONE, run_context, visible_intraday

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asof", default=datetime.now(ZONE).date().isoformat(), help="Analysis date YYYY-MM-DD")
    parser.add_argument("--slot", default="auto", choices=["auto", "morning", "midday", "closing", "refresh", "preclose"])
    parser.add_argument("--serve", action="store_true", help="Launch local dashboard")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    fixture = json.loads((ROOT / "data/market_snapshot.json").read_text(encoding="utf-8"))
    facts=json.loads((ROOT/"data/facts_reference.json").read_text(encoding="utf-8")).get("records",{})
    news=json.loads((ROOT/"data/news.json").read_text(encoding="utf-8"))
    report = build_report(fixture, args.asof, facts=facts, news=news.get("articles",[]))
    health_file=ROOT/"data/health.json"
    report["health"] = json.loads(health_file.read_text()) if health_file.exists() else {
        "result":"not_configured","message":"Collecte automatique non encore exécutée"}
    now = datetime.now(ZONE)
    report["runtime"] = run_context(now, schedule=os.environ.get("NOUR_SCHEDULE", ""),
        event=os.environ.get("GITHUB_EVENT_NAME", "local"), slot=args.slot,
        started_at=os.environ.get("NOUR_STARTED_AT"), run_id=os.environ.get("GITHUB_RUN_ID", ""),
        commit=os.environ.get("GITHUB_SHA", ""))
    live_path = ROOT/"data/intraday.json"
    live = json.loads(live_path.read_text()) if live_path.exists() else None
    report["intraday"] = visible_intraday(live, now)
    for item in report["results"]:
        item["intraday_quote"] = report["intraday"]["quotes"].get(item["symbol"])
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
    for key,b in editions.items():
        b["edition_links"] = links
        atomic_json(ROOT/f"web/briefing-{EDITIONS[key]}.json", b)
    atomic_json(ROOT/"web/runtime.json", {**report["runtime"], "market":report["health"],
                "last_closed_session":briefing["market_session"],
                "intraday_status":report["intraday"]["status"], "briefings":links,
                "publication_stage":"built_before_pages_deployment"})
    target = ROOT / "web/report.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ROOT/"web/news.json").write_text(json.dumps(news,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (ROOT/"web/briefing.json").write_text(json.dumps(briefing,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    build_site(fixture, report, ROOT / "web", briefing=briefing, editions=editions)
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
