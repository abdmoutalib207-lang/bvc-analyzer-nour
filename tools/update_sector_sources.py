"""Refresh official sector publication link metadata (no numeric extraction)."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nour.market import atomic_json
from nour.sector_sources import collect, read_config, validate_state


def main(root=ROOT):
    target = root / "data/sector_source_candidates.json"
    health = root / "data/sector_source_health.json"
    try:
        config = read_config(root / "data/sector_source_watch.json")
        previous = json.loads(target.read_text(encoding="utf-8")) if target.exists() else None
        if previous is not None:
            validate_state(previous)
        state = collect(config, previous)
    except (ValueError, json.JSONDecodeError) as exc:
        atomic_json(health, {
            "schema_version": 1, "checked_at": datetime.now(timezone.utc).isoformat(),
            "status": "error", "message": str(exc)[:200],
            "last_good_preserved": True, "usable_for_score": False})
        return 1
    atomic_json(target, state)
    atomic_json(health, {
        "schema_version": 1, "checked_at": state["checked_at"],
        "status": state["status"], "source_count": len(state["sources"]),
        "successful": sum(x["status"] == "success" for x in state["sources"].values()),
        "failed": sorted(k for k, x in state["sources"].items() if x["status"] == "error"),
        "usable_for_score": False, "scope": "publications sectorielles candidates, pas de chiffres financiers"})
    print(f'Sector sources: {state["status"]}, '
          f'{sum(x["status"] == "success" for x in state["sources"].values())}/'
          f'{len(state["sources"])} pages fetched; no issuer ratios changed')
    return 0


if __name__ == "__main__":
    sys.exit(main())
