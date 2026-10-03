"""Fetch the latest completed CDG session into Nour; no access to the old repo."""
import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from nour.market import CANCELLED_SESSIONS, atomic_json, capture_intraday, fetch_cdg, import_session


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Previously captured raw CDG JSON array (offline test)")
    args=parser.parse_args()
    data=ROOT/"data"
    now=datetime.now(ZoneInfo("Africa/Casablanca"))
    status={"checked_at":now.isoformat(),"source":"CDG Capital Bourse",
            "result":"error", "last_session":None, "message":""}
    try:
        fixture=json.loads((data/"market_snapshot.json").read_text())
        mapping=json.loads((data/"source_codes.json").read_text())
        raw=json.loads(args.input.read_text()) if args.input else fetch_cdg()
        if now.weekday() < 5 and now.hour < 16 and now.date().isoformat() not in CANCELLED_SESSIONS:
            point = capture_intraday(fixture, raw, mapping, now=now)
            atomic_json(data/"intraday.json", point)
            count = len(point["quotes"])
            status.update(result="intraday" if count else "awaiting_quotes",
                          last_session=fixture["market"].get("last_session"),
                          message=f"{count} observations provisoires ; clôtures et scores historiques inchangés",
                          intraday_session=point["session"], rejected=point["rejected"])
            atomic_json(data/"health.json", status)
            print(json.dumps(status,ensure_ascii=False))
            return
        candidate,details=import_session(fixture,raw,mapping,now=now)
        status.update(last_session=details["session"],details=details)
        conflicting = len(details["conflicts"])
        if details["new_bars"]:
            atomic_json(data/"market_snapshot.json",candidate)
            status.update(result="partial" if conflicting else "updated",
                          message=f"{details['new_bars']} bougies validées ; {conflicting} conflit(s) conservés")
        else:
            status.update(result="conflict" if conflicting else "unchanged",
                          message=(f"{conflicting} bougie(s) divergente(s) non remplacée(s)"
                                   if conflicting else "Aucune nouvelle séance vérifiée"))
    except Exception as exc:
        status["message"]=f"Collecte refusée : {exc}"
        atomic_json(data/"health.json",status)
        raise
    atomic_json(data/"health.json",status)
    print(json.dumps(status,ensure_ascii=False))


if __name__=="__main__": main()
