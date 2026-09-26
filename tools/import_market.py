"""Copy public-market snapshots from a separate checkout into Nour; never write there."""
import argparse
import hashlib
import json
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / "audit_20260926" / "repo"
DEST = Path(__file__).resolve().parents[1] / "data" / "market_snapshot.json"
SOURCE_COMMIT = "dd8e89f29f6e6777f783db634a12fcccb3d5088a"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def import_market(source=SOURCE, dest=DEST):
    source, dest = Path(source), Path(dest)
    market_file = source / "data.json"
    historic_dir = source / "pipeline" / "candles"
    market = json.loads(market_file.read_text(encoding="utf-8"))
    records, history_hashes = {}, {}
    for ticker in market["tickers"]:
        symbol = ticker["symbol"]
        p = historic_dir / f"{symbol}.json"
        candles = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
        if p.exists():
            history_hashes[symbol] = sha(p)
        meta = ticker.get("_meta", {})
        records[symbol] = {
            "symbol": symbol, "name": ticker.get("name", symbol), "sector": ticker.get("sector", ""),
            "price": ticker.get("price"), "day_turnover_mad": ticker.get("echange_dh"),
            "day_shares": ticker.get("vol"), "price_asof": meta.get("prix_asof"),
            "price_source": meta.get("source_prix"), "stale": meta.get("stale"),
            "suspended": meta.get("suspendu"), "resumed_recently": meta.get("reprise_recente"),
            "sessions_since_resume": meta.get("seances_depuis_reprise"),
            "fundamentals": {"per": ticker.get("pe"), "pb": ticker.get("pb"),
                             "dividend_yield_pct": ticker.get("div"),
                             "source": meta.get("source_fond"), "asof": meta.get("fond_asof")},
            "legacy_sig": ticker.get("sig"), "legacy_sig_bvc": ticker.get("sigBvc"),
            "candles": candles, "full_history_count_reported": len(candles),
        }
    payload = {
        "project": "BVC Analyzer Nour", "schema_version": 2,
        "snapshot_updated": market["updated"], "source_commit": SOURCE_COMMIT,
        "market": {"status": market.get("market_status"), "masi": market.get("masi", {})},
        "source_files": {"data.json": sha(market_file), "pipeline/candles": history_hashes},
        "symbols": sorted(records), "records": records,
        "note": "Archive du projet principal copiée en lecture seule; années couvertes variables selon le titre.",
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--destination", type=Path, default=DEST)
    args = parser.parse_args()
    result = import_market(args.source, args.destination)
    print(len(result["records"]), "titres;", sum(bool(r["candles"]) for r in result["records"].values()), "historiques;", args.destination)
