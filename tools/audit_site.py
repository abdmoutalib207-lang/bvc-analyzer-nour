"""Audit generated assistant assets and snapshot parity; no live provider call."""
import json
from html import escape
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nour.assistant import build_data, read_briefings, read_history_files
from nour.sector_audit import audit_sector_report
from nour.economic_sources import load_catalog, catalog_summary


def audit(web):
    web = Path(web)
    report = json.loads((web/'report.json').read_text())
    actual = json.loads((web/'assistant-data.json').read_text())
    if actual != build_data(report,read_briefings(web,report['analysis_date']),
                            read_history_files(web,[r['symbol'] for r in report['results']])):
        raise ValueError('Assistant facts diverge from the published report')
    sector = json.loads((web/'sector-readiness.json').read_text())
    if sector != audit_sector_report(report):
        raise ValueError('Sector evidence JSON diverges from the published report')
    sector_page = (web/'metiers.html').read_text()
    for row in report['results']:
        if f'href="titres/{row["symbol"]}.html"' not in sector_page:
            raise ValueError(f'Missing issuer on métier review page: {row["symbol"]}')
    if sector.get('documents_certified') is not False:
        raise ValueError('Sector review must never claim whole-document certification')
    source_summary = json.loads((web/'economic-sources-summary.json').read_text())
    if source_summary != catalog_summary(load_catalog()):
        raise ValueError('Economic source summary diverges from its registry')
    source_page = (web/'sources.html').read_text()
    for source in load_catalog()['institutions']:
        if escape(source['name']) not in source_page:
            raise ValueError('Missing economic institution: ' + source['id'])
    if source_summary['usable_for_score'] or source_summary['usable_to_certify_issuer_financial_facts']:
        raise ValueError('Economic context cannot certify company accounts')
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
