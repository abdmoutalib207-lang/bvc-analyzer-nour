"""Reproducible morning/closing briefings: observed facts and explicit scenarios."""
from __future__ import annotations

from datetime import date, datetime, timedelta


def create_briefing(report, watch=("ADI","RDS","TGCC","SGTM","CMGP","MSA","SMI","T2S","CMT")):
    market = report.get("market", {})
    masi = market.get("masi") or {}
    asof = report["analysis_date"]
    latest_dates = [r["asof"] for r in report["results"] if r["asof"]]
    session = max(latest_dates) if latest_dates else None
    active = [r for r in report["results"] if r["asof"] == session and r["decision"] != "INDISPONIBLE"]
    previous = (date.fromisoformat(asof)-timedelta(days=4)).isoformat()
    news = [a for a in report.get("news", []) if a.get("published_at","")[:10] >= previous][:12]
    focus = []
    by = {r["symbol"]:r for r in report["results"]}
    for symbol in watch:
        if symbol not in by: continue
        r=by[symbol];t=r["technical"];s=r["canonical_score"]
        focus.append({"symbol":symbol,"name":r["name"],"price":r["price"],"asof":r["asof"],
                      "data_status":r["decision"],"score":s["value"],"score_state":s["state"],
                      "support":t["support20"],"resistance":t["resistance20"],
                      "rsi":t["rsi14"],"activity":t["volume_vs_median20"],
                      "scenario": ("Attendre des séances comparables après la reprise" if t["limited_by_resumption"]
                                   else "Surveiller la tenue du support et le franchissement confirmé de la résistance" if
                                   t["support20"] is not None and t["resistance20"] is not None else
                                   "Données insuffisantes pour établir des niveaux"),
                      "issues":r["quality"]["issues"][:2]})
    index_current = masi.get("asof") == session and session is not None
    return {"schema_version":1,"generated_for":asof,"market_session":session,
            "snapshot_updated":report["snapshot_updated"],"market_status":market.get("status"),
            "coverage": {"titles":len(report["results"]), "quoted_session":len(active),
                         "observable":sum(x["decision"]=="OBSERVABLE" for x in active)},
            "index":masi if index_current else None,
            "index_notice":None if index_current else "MASI non confirmé à la date de la dernière séance : valeur archivée écartée du briefing.",
            "focus":focus,"news":news,"news_role":"veille uniquement",
            "limitations":"Scénarios descriptifs sans probabilités estimées ni prédiction de rendement; frais, carnet et flux non observés."}
