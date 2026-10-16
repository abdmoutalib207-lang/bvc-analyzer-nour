"""Index official report candidates; does not alter financial facts or scores."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nour.market import atomic_json
from nour.official_sources import collect, validate_registry, validate_state


def main(argv=None, root=ROOT):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--symbols', nargs='+')
    parser.add_argument('--fetch-documents', action='store_true')
    parser.add_argument('--max-documents', type=int, default=10)
    args = parser.parse_args(argv)
    target = root / 'data/official_document_candidates.json'
    health = root / 'data/official_sources_health.json'
    try:
        registry = json.loads((root / 'data/official_sources.json').read_text())
        validate_registry(registry)
        previous = json.loads(target.read_text()) if target.exists() else None
        if previous is not None:
            validate_state(previous)
        result = collect(registry, previous, symbols=args.symbols,
                         fetch_documents=args.fetch_documents, max_documents=args.max_documents,
                         cache_dir=root / '.cache/official-documents' if args.fetch_documents else None)
    except (json.JSONDecodeError, ValueError) as exc:
        atomic_json(health, {'schema_version': 1, 'checked_at': datetime.now(timezone.utc).isoformat(),
                            'status': 'error', 'error': str(exc)[:240],
                            'candidate_file_preserved': True})
        print('Sources officielles : état invalide, candidats conservés', file=sys.stderr)
        return 1
    atomic_json(target, result)
    atomic_json(health, {
        'schema_version': 1, 'checked_at': result['checked_at'], 'status': result['status'],
        'sources': result['sources'], 'candidate_count': len(result['documents']),
        'scope': 'indexation seulement; aucun chiffre extrait ni certifié'})
    print(f"Sources officielles : {result['status']}, {len(result['documents'])} candidats (non analysés)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
