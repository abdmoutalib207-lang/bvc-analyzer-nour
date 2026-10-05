"""Collect two fixed public primary PDFs for manual review; never import ratios.

Temporary PDFs are not committed. Only selected page text, rendered page images
and their source hashes are retained. A failure is recorded, never relabelled as
verified evidence. No issuer sign-in, CAPTCHA, or account session is used.
"""
import hashlib
import base64
import json
import subprocess
import tempfile
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'docs/reviews/2026-10-05'
SOURCES = {
    'EQD-annual': ('https://www.ammc.ma/sites/default/files/Eqdom_RFA_2025.pdf', [55, 58, 59, 63]),
    'CASH-ipo': ('https://www.ammc.ma/sites/default/files/NO_CASHPLUS_036_2025.pdf', [4, 9, 10, 11, 39]),
}


def collect(item):
    label, (url, pages) = item
    result = dict(source_url=url, status='unavailable')
    try:
        with tempfile.TemporaryDirectory(prefix='nour-primary-review-') as temporary:
            pdf = Path(temporary) / 'source.pdf'
            request = urllib.request.Request(url, headers={'User-Agent': 'BVC-Nour-primary-review/1.0'})
            with urllib.request.urlopen(request, timeout=45) as response:
                content = response.read(32 * 1024 * 1024 + 1)
            if len(content) > 32 * 1024 * 1024 or not content.startswith(b'%PDF-'):
                raise ValueError('Not a PDF or exceeds 32 MiB; no access-wall workaround')
            pdf.write_bytes(content)
            text = Path(temporary) / 'source.txt'
            subprocess.run(['pdftotext', '-layout', str(pdf), str(text)], check=True)
            parts = text.read_text().split('\f')
            retained = []
            for page in pages:
                if page > len(parts) or not parts[page - 1].strip():
                    continue
                (OUTPUT / f'{label}-p{page}.txt').write_text(parts[page - 1])
                subprocess.run(['pdftoppm', '-f', str(page), '-l', str(page), '-singlefile',
                                '-scale-to', '2200', '-jpeg', str(pdf),
                                str(OUTPUT / f'{label}-p{page}')], check=True)
                print('NOUR_PRIMARY_PAGE ' + json.dumps(dict(
                    label=label, page=page, text=parts[page - 1],
                    jpeg=base64.b64encode((OUTPUT / f'{label}-p{page}.jpg').read_bytes()).decode())))
                retained.append(page)
            result.update(status='downloaded_pending_manual_visual_review', bytes=len(content),
                          document_hash='sha256:' + hashlib.sha256(content).hexdigest(),
                          selected_pdf_pages=retained)
    except Exception as error:
        result['error'] = f'{type(error).__name__}: {error}'
    return label, result


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        evidence = dict(pool.map(collect, SOURCES.items()))
    (OUTPUT / 'manifest.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(evidence, ensure_ascii=False))


if __name__ == '__main__':
    main()
