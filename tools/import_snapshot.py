"""Freeze a small, auditable public-market fixture; never writes to the source repository."""
import argparse
import hashlib
import json
from pathlib import Path

PILOTS = ("ADI", "RDS", "T2S", "TGCC", "SGTM", "CMT", "SMI", "MSA")
DEFAULT_SOURCE = Path(__file__).resolve().parents[2] / "audit_20260926" / "repo"
DEST = Path(__file__).resolve().parents[1] / "data" / "pilot_snapshot.json"
COMMIT = "dd8e89f29f6e6777f783db634a12fcccb3d5088a"


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze(source, destination):
    source = Path(source)
    data_path = source / "data.json"
    history_path = source / "pipeline" / "historical_data.json"
    source_data = json.loads(data_path.read_text(encoding="utf-8"))
    history = json.loads(history_path.read_text(encoding="utf-8"))
    tickers = {item["symbol"]: item for item in source_data["tickers"]}
    records = {}
    for symbol in PILOTS:
        snap = tickers[symbol]
        assert symbol in history, f"Missing historical ticker {symbol}"
        meta = snap.get("_meta", {})
        records[symbol] = {
            "symbol": symbol, "name": snap["name"], "price": snap.get("price"),
            "day_turnover_mad": snap.get("echange_dh"), "day_shares": snap.get("vol"),
            "price_asof": meta.get("prix_asof"), "price_source": meta.get("source_prix"),
            "stale": meta.get("stale"), "suspended": meta.get("suspendu"),
            "resumed_recently": meta.get("reprise_recente"),
            "sessions_since_resume": meta.get("seances_depuis_reprise"),
            "legacy_sig": snap.get("sig"), "legacy_sig_bvc": snap.get("sigBvc"),
            "candles": history[symbol]["candles"],
            "full_history_count_reported": history[symbol].get("n_candles"),
        }
    payload = {
        "project": "BVC Analyzer Nour", "schema_version": 1,
        "snapshot_updated": source_data["updated"],
        "source_commit": COMMIT,
        "source_files": {
            "data.json": file_hash(data_path),
            "pipeline/historical_data.json": file_hash(history_path),
        }, "symbols": list(PILOTS), "records": records,
        "note": "Frozen source extract. Past turnover is an estimate (close × shares); do not use as actual traded value.",
    }
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--destination", type=Path, default=DEST)
    args = parser.parse_args()
    print("Frozen", len(freeze(args.source, args.destination)["records"]), "in", args.destination)
