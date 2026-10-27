"""Prepare bounded primary evidence for human review; never publish financial facts."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nour.sector_ingestion import download, pdf_pages, plain

DEFAULT = 'BCP,BOA,BMC,CDM,CIH,CFGB,SAF,AFM,AGM,IMI,BAL'
PATTERN = re.compile(r'referentiel|normes (?:comptables|ifrs|internationales)|principes comptables|juste valeur|cout amorti|comptabilisation.*(?:commissions|revenus)')


def selected_records(facts, symbols):
    selected = list(dict.fromkeys(symbols))
    if not selected or len(selected) > 12 or any(s not in facts for s in selected):
        raise ValueError('Choisir de un à douze titres du référentiel Nour')
    return [(s, facts[s]) for s in selected]


def candidate_pages(pages):
    result = []
    for n, text in enumerate(pages, 1):
        hits = [line.strip() for line in text.splitlines() if PATTERN.search(plain(line))]
        if hits:
            result.append(dict(page=n, hits=hits[:8], score=len(hits)))
    return sorted(result, key=lambda r: (-r['score'], r['page']))[:12]


def prepare(symbol, record, output, cache, fetch=download, reader=pdf_pages):
    result = dict(symbol=symbol, url=record.get('url'), exercise=record.get('exercice'),
                  status='unavailable', visual_review=False, used_for_score=False)
    try:
        source = fetch(record['url'], {'hosts':['www.ammc.ma']}, cache)
        target = output/(symbol+'.pdf')
        shutil.copyfile(source, target)
        raw = target.read_bytes()
        if not raw.startswith(b'%PDF-'):
            raise ValueError('not_pdf')
        result['sha256'] = sha256(raw).hexdigest()
        pages = reader(target)
        (output/(symbol+'.txt')).write_text('\f'.join(pages), encoding='utf-8')
        result.update(status='candidate_only', pages=len(pages), candidates=candidate_pages(pages))
    except Exception as error:
        # No exception messages, response bodies or credentials enter the log.
        result['failure_class'] = type(error).__name__
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--symbols', default=DEFAULT)
    p.add_argument('--output', type=Path, default=ROOT/'.cache/accounting-review')
    p.add_argument('--cache', type=Path, default=ROOT/'.cache/sector-pdf')
    args = p.parse_args()
    facts = json.loads((ROOT/'data/facts_reference.json').read_text())['records']
    selected = selected_records(facts, args.symbols.split(','))
    args.output.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(lambda item: prepare(*item,args.output,args.cache), selected))
    manifest = dict(version='nour-accounting-review-candidates-v1',
        observed_at=datetime.now(timezone.utc).isoformat(), records=rows,
        visual_review=False, used_for_score=False, promoted_facts=0)
    (args.output/'review.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(manifest,ensure_ascii=False))
    if all(r['status']=='unavailable' for r in rows):
        raise SystemExit('Aucun document primaire récupéré ; aucune promotion')


if __name__ == '__main__':
    main()
