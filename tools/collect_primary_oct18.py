"""Collect fixed public annual reports for manual review, never import facts."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SYMBOLS = ('TGCC', 'SGTM', 'CMGP', 'AGM', 'AFM', 'CFGB', 'ATL', 'WAF')
OUTPUT = ROOT / 'tmp/primary-oct18'


def collect(item):
    symbol, url = item
    row = dict(url=url, status='unavailable')
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'BVC-Nour-document-review/1.0'})
        with urllib.request.urlopen(request, timeout=45) as response:
            if response.geturl() != url:
                raise ValueError('Source URL redirected; manual review required')
            content = response.read(32*1024*1024+1)
        if len(content) > 32*1024*1024 or not content.startswith(b'%PDF-'):
            raise ValueError('Invalid PDF or size exceeds 32 MiB')
        (OUTPUT / (symbol+'.pdf')).write_bytes(content)
        row.update(status='downloaded_pending_manual_review', bytes=len(content),
                   document_hash='sha256:'+hashlib.sha256(content).hexdigest())
    except Exception as exc:
        row['error'] = type(exc).__name__
    return symbol, row


def main():
    records = json.loads((ROOT/'data/facts_reference.json').read_text())['records']
    sources = [(s, records[s]['url']) for s in SYMBOLS]
    if any(not u.startswith('https://www.ammc.ma/sites/default/files/') or not u.endswith('.pdf') for _,u in sources):
        raise ValueError('Unexpected report origin')
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        result = dict(pool.map(collect, sources))
    manifest = dict(collected_at=datetime.now(timezone.utc).isoformat(),
                    scope='Public PDFs only, no facts imported; awaiting visual review', documents=result)
    (OUTPUT/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == '__main__':
    main()
