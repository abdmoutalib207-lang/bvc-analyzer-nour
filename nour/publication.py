"""Observable publication health and history depth; never changes scores."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

OUTCOMES = {
    'updated': 'Nouvelle séance intégrée',
    'partial': 'Intégration partielle · observations refusées pour conflit',
    'conflict': 'Nouvelle observation refusée pour conflit',
    'unchanged': 'Aucune nouveauté',
    'reconciled': 'Séance rapprochée entre fournisseurs',
    'error': 'Source indisponible ou observation invalide',
    'intraday': 'Observation provisoire · aucune clôture intégrée',
    'awaiting_quotes': 'En attente de transactions',
}


def history_readiness(item):
    total = (item.get('quality') or {}).get('usable_close_bars', 0)
    tech = item.get('technical') or {}
    usable = tech.get('sessions', total)
    resumed = bool(tech.get('limited_by_resumption'))
    depth = 'none' if not usable else 'short' if usable < 252 else 'deep'
    suspended = (item.get('issuer_status') or {}).get('trading_status') == 'suspended'
    description = ('aucune séance exploitable' if not usable else
                   f'{usable} séances post-reprise' if resumed else
                   f'historique {"profond" if depth == "deep" else "court"} · {usable} séances')
    return {'state': item.get('decision'), 'depth': depth,
            'validated_close_sessions': total, 'indicator_sessions': usable,
            'post_resume_only': resumed, 'last_close': item.get('asof'),
            'age_calendar_days': item.get('age_calendar_days'),
            'deep_threshold_sessions': 252,
            'label': ('Cotation suspendue · absence de transactions documentée · dossier historique' if suspended and not usable else
                      f'{item.get("decision")} · {description} · dernière clôture {item.get("asof") or "indisponible"}'),
            'notice': 'Profondeur descriptive, sans modifier les seuils de calcul, la qualité ni le score.'}


def collection_view(health):
    result = health.get('result', 'not_observed')
    return {'result': result, 'label': OUTCOMES.get(result, 'Collecte non observée'),
            'checked_at': health.get('checked_at'), 'last_session': health.get('last_session'),
            'message': health.get('message'),
            'conflicts': deepcopy((health.get('details') or {}).get('conflicts') or []),
            'fully_validated': result in ('updated', 'unchanged', 'reconciled')}


def provenance(snapshot_commit, generator_commit, fixture_path=None):
    return {'source_snapshot_commit': snapshot_commit, 'generator_commit': generator_commit or None,
            'publication_commit': None, 'publication_manifest': 'publication.json',
            'publication_commit_status': 'resolved_in_artifact_manifest_after_data_commit',
            'market_snapshot_sha256': hashlib.sha256(Path(fixture_path).read_bytes()).hexdigest() if fixture_path else None,
            'notice': 'Le commit de publication est enregistré après sauvegarde des exports. Une construction locale ne prouve pas un déploiement.'}


def publication_manifest(web, commit, run_id='', generated_at=''):
    if len(commit) != 40 or any(c not in '0123456789abcdef' for c in commit):
        raise ValueError('Publication commit must be an exact Git SHA')
    web = Path(web)
    files = ('report.json', 'assistant-data.json', 'assistant-context.json', 'runtime.json', 'index.html')
    hashes = {p: hashlib.sha256((web/p).read_bytes()).hexdigest() for p in files}
    report = json.loads((web/'report.json').read_text())
    return {'schema_version': 'nour-publication-v1', **report.get('provenance', {}),
            'publication_commit': commit, 'publication_commit_status': 'artifact_recorded',
            'stage': 'artifact_prepared_for_deployment', 'run_id': str(run_id),
            'generated_at': generated_at, 'sha256': hashes,
            'notice': 'Identité de l’artefact préparé ; vérifier le workflow Pages pour confirmer le déploiement.'}
