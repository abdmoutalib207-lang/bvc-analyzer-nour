"""Refresh Nour directly from CDG, preserving the last valid data on failure."""
import json
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nour.market import CASABLANCA, atomic_json
from nour.overview import fetch_indices, update_overview


def main():
    data = ROOT / 'data'
    now = datetime.now(CASABLANCA)
    try:
        previous = json.loads((data/'market_overview.json').read_text())
        history = json.loads((data/'masi_history.json').read_text())
        updated, series = update_overview(previous, history, fetch_indices(), [], now)
        atomic_json(data/'masi_history.json', series)
        atomic_json(data/'market_overview.json', updated)
        atomic_json(data/'overview_health.json', {'result': 'updated', 'checked_at': now.isoformat(),
                                                'asof': updated['current']['asof']})
        print('MASI et séance CDG :', updated['current']['asof'])
    except Exception as exc:
        atomic_json(data/'overview_health.json', {'result': 'error', 'checked_at': now.isoformat(),
                                                'message': str(exc)})
        raise


if __name__ == '__main__':
    main()
