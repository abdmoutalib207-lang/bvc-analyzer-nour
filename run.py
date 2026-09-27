"""Build the complete static research site and optionally serve it locally."""
import argparse
import json
from datetime import date
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from nour.engine import build_report
from nour.site import build_site
from nour.briefing import create_briefing

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asof", default=date.today().isoformat(), help="Analysis date YYYY-MM-DD")
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
    briefing=create_briefing(report)
    target = ROOT / "web/report.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ROOT/"web/news.json").write_text(json.dumps(news,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (ROOT/"web/briefing.json").write_text(json.dumps(briefing,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    build_site(fixture, report, ROOT / "web", briefing=briefing)
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
