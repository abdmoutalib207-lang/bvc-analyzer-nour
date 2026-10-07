"""Audit generated assistant assets and snapshot parity; no live provider call."""
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nour.assistant import build_data, read_briefings, read_history_files


def audit(web):
    web = Path(web)
    report = json.loads((web/'report.json').read_text())
    actual = json.loads((web/'assistant-data.json').read_text())
    if actual != build_data(report,read_briefings(web,report['analysis_date']),
                            read_history_files(web,[r['symbol'] for r in report['results']])):
        raise ValueError('Assistant facts diverge from the published report')
    config = json.loads((web/'assistant-config.json').read_text())
    if config.get('endpoint') is not None:
        raise ValueError('Public LLM must not be enabled without its protected backend')
    pages = list(web.glob('*.html')) + list((web/'titres').glob('*.html'))
    for page in pages:
        text = page.read_text()
        prefix = '../' if page.parent.name == 'titres' else ''
        for needle in ('id="assistant-dialog"', f'src="{prefix}assistant.js"',
                       f'href="{prefix}assistant.css"',f'src="{prefix}assistant-domains.js"',
                       f'src="{prefix}research.js"'):
            if text.count(needle) != 1:
                raise ValueError(f'{page.name}: missing or duplicated assistant asset {needle}')
    for path in [web/'assistant.js', web/'assistant-config.json', web/'assistant-data.json']:
        if re.search(r'\bsk-[a-zA-Z0-9_-]{20,}', path.read_text()):
            raise ValueError(f'Possible credential in {path.name}')
    print(f'Assistant audit: {len(pages)} pages, {len(actual["symbols"])} titles, '
          f'{len(actual["masi_history"])} MASI sessions; exact report parity, public LLM disabled')


if __name__ == '__main__':
    audit(ROOT/'web')
