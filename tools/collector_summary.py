"""Workflow summary reports data outcomes, not just a process exit code."""
import json
import os
from pathlib import Path


def summary(data):
    out = ['## Nour : état réel des collectes', '', '| Collecte | État des données |', '| --- | --- |']
    for label, filename in [('Marché', 'health.json'), ('Actualités', 'news_health.json'),
                            ('Sources officielles', 'official_sources_health.json'),
                            ('MASI', 'overview_health.json'), ('Volumes multisources', 'market_integrity.json')]:
        try:
            record = json.loads((Path(data)/filename).read_text())
            status = record.get('result') or record.get('status') or 'non observé'
            message = str(record.get('message') or '').replace('|', '/').replace('\n', ' ')
            conflicts = len((record.get('details') or {}).get('conflicts') or [])
            out.append(f'| {label} | {status} · {message} · {conflicts} conflit(s) |')
        except (OSError, ValueError):
            out.append(f'| {label} | Diagnostic indisponible |')
    return '\n'.join(out)+'\n'


if __name__ == '__main__':
    result = summary(Path(__file__).resolve().parents[1]/'data')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as out:
            out.write(result)
    print(result)
