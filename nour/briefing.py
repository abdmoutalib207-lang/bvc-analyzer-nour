"""Reproducible morning/closing briefings: observed facts and explicit scenarios."""
from __future__ import annotations

from datetime import date, datetime, timedelta
import re


# The complete news page can carry broader context. A market briefing must not
# let an unrelated cultural or political headline displace an issuer release.
MARKET_WORDS = re.compile(
    r"\b(?:bourse|boursier|masi|ammc|dividende|capitalisation|actionnaires?|"
    r"résultats?\s+financiers?|bénéfices?|chiffre\s+d'affaires|"
    r"taux\s+directeur|bank\s+al.maghrib|banques?|financement|"
    r"cotation|introduction\s+en\s+bourse|obligations?|"
    r"minier|ciment|semestre|immobilier|trésor|adjudication)\b",
    re.IGNORECASE,
)


def market_relevant(article):
    return (article.get("tier") == "S1" or bool(article.get("tickers"))
            or bool(MARKET_WORDS.search(article.get("title") or "")))


def level_scenario(price, support, resistance, resumed=False):
    if resumed:
        return "Attendre des séances comparables après la reprise"
    if price is None or support is None or resistance is None:
        return "Données insuffisantes pour établir des niveaux"
    if price < support:
        return "Clôture sous le support de référence ; vérifier une éventuelle reconquête, sans présumer de sa direction future"
    if price > resistance:
        return "Clôture au-dessus de la résistance de référence ; vérifier si ce niveau se maintient"
    return "Surveiller la tenue du support et le franchissement confirmé de la résistance"


def create_briefing(report, watch=("ADI","RDS","TGCC","SGTM","CMGP","MSA","SMI","T2S","CMT"), closing_only=False):
    market = report.get("market", {})
    overview = report.get('market_overview') or {}
    masi = overview.get('masi') or market.get("masi") or {}
    asof = report["analysis_date"]
    latest_dates = [r["asof"] for r in report["results"] if r["asof"]]
    session = (overview.get('asof') if closing_only else max(latest_dates) if latest_dates else None)
    active = [r for r in report["results"] if r["asof"] == session and r["decision"] != "INDISPONIBLE"]
    news_cutoff = session if closing_only and session else asof
    previous = (date.fromisoformat(news_cutoff)-timedelta(days=4)).isoformat()
    news = [a for a in report.get("news", [])
            if previous <= a.get("published_at", "")[:10] <= news_cutoff and market_relevant(a)]
    # Official issuer documents precede secondary alerts; within each tier,
    # retain date order. This is editorial order, never a scoring factor.
    news = sorted(news, key=lambda a: (a.get("tier") == "S1", bool(a.get('tickers')), a.get("published_at", "")),
                  reverse=True)[:24]
    focus = []
    by = {r["symbol"]:r for r in report["results"]}
    for symbol in watch:
        if symbol not in by: continue
        r=by[symbol];t=r["technical"];s=r["canonical_score"]
        if closing_only and r['asof'] != session: continue
        focus.append({"symbol":symbol,"name":r["name"],"price":r["price"],"asof":r["asof"],
                      "data_status":r["decision"],"score":s["value"],"score_state":s["state"],
                      "support":t["support20"],"resistance":t["resistance20"],
                      "rsi":t["rsi14"],"activity":t["volume_vs_median20"],
                      "scenario": level_scenario(r["price"], t["support20"],
                                                  t["resistance20"], t["limited_by_resumption"]),
                      "issues":r["quality"]["issues"][:2]})
        focus[-1]["intraday_quote"] = None if closing_only else r.get("intraday_quote")
    index_current = masi.get("asof") == session and session is not None
    from .editorial import market_reading, title_reading
    editorial = market_reading(report, overview if index_current else {}, session)
    for f in focus:
        f['reading'] = title_reading(by[f['symbol']],session,editorial['previous_session'],
                                    masi.get('change_pct') if index_current and not editorial['provisional'] else None)
        f['publications'] = [a for a in news if f['symbol'] in a.get('tickers', [])][:3]
        if f['asof'] == session:
            editorial['vigilance'].append(f'{f["symbol"]} : {f["scenario"]}' +
                (f' (références {f["support"]} / {f["resistance"]} MAD).' if f['support'] is not None and f['resistance'] is not None else '.'))
    macro_words = re.compile(r'\b(?:brent|pétrole|inflation|bank.al.maghrib|taux.directeur|fed|trésor|dollar|change)\b', re.I)
    context = [a for a in news if macro_words.search(a.get('title',''))]
    fundamental_count = sum(bool(r.get('fundamental',{}).get('document_url')) for r in report['results'])
    from .market_view import closing_summary
    runtime = report.get("runtime") or {}
    closing_pending = runtime.get("slot") == "closing" and session != asof
    return {"schema_version":2,"editorial_version":"nour-briefing-v2","generated_for":asof,"market_session":session,
            "runtime":runtime, "title":runtime.get("label", "Point de séance"),
            "intraday":report.get("intraday") or {},
            "edition_status":"closing_pending" if closing_pending else "published",
            "edition_notice":("Clôture du jour non confirmée par la collecte : dernières données datées conservées."
                              if closing_pending else None),
            "snapshot_updated":report["snapshot_updated"],"market_status":market.get("status"),
            "coverage": {"titles":len(report["results"]), "quoted_session":len(active),
                         "observable":sum(x["decision"]=="OBSERVABLE" for x in active)},
            "index":masi if index_current else None,
            "market_summary":closing_summary(overview) if index_current and overview else None,
            "index_notice":None if index_current else "MASI non confirmé à la date de la dernière séance : valeur archivée écartée du briefing.",
            "focus":focus,"news":news,"news_role":"veille uniquement", "editorial":editorial,
            "context_news":context,"fundamental_coverage":{"referenced":fundamental_count,"titles":len(report['results'])},
            "limitations":"Scénarios descriptifs sans probabilités estimées ni prédiction de rendement; frais, carnet et flux non observés."}
