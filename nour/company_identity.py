"""Local, attributed issuer marks; a missing mark is a ticker, never invented art."""
from functools import lru_cache
from html import escape
import json
from pathlib import Path
import re
import hashlib
import base64
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def catalog():
    path = ROOT/'data/company_logos.json'
    return json.loads(path.read_text(encoding='utf-8'))['records'] if path.exists() else {}


def validate_svg(data):
    lower = data.lower()
    if b'<!doctype' in lower or b'<!entity' in lower:
        raise ValueError('SVG document declarations refused')
    tree = ET.fromstring(data)
    if tree.tag.split('}')[-1] != 'svg':
        raise ValueError('Expected SVG root')
    for node in tree.iter():
        if node.tag.split('}')[-1].lower() in ('script','foreignobject','iframe','object','embed','animate','set'):
            raise ValueError('Active SVG content refused')
        for key,value in node.attrib.items():
            key = key.split('}')[-1].lower()
            if key.startswith('on'):
                raise ValueError('SVG event handler refused')
            if key in ('href','src') and not value.startswith('#'):
                if not value.startswith('data:image/png;base64,'):
                    raise ValueError('External SVG reference refused')
                embedded = base64.b64decode(value.split(',',1)[1], validate=True)
                if not embedded.startswith(b'\x89PNG\r\n\x1a\n'):
                    raise ValueError('Invalid embedded PNG')
            if 'url(' in value and re.search(r'url\(\s*[\"\x27]?(?!#)', value):
                # Local gradients and clip paths are the only CSS references.
                if any(not token.strip(' \"\x27').startswith('#') for token in re.findall(r'url\(([^)]*)\)',value)):
                    raise ValueError('External SVG style refused')
        if node.tag.split('}')[-1] == 'style' and re.search(r'@import|https?:|url\((?!\s*#)', node.text or '',re.I):
            raise ValueError('External SVG stylesheet refused')


def validate_catalog(symbols):
    marks = catalog()
    if set(marks) != set(symbols):
        raise ValueError('Logo catalog and issuer universe differ')
    for symbol,mark in marks.items():
        if mark.get('status') != 'verified':
            continue
        filename = mark.get('filename') or ''
        if not re.fullmatch(re.escape(symbol)+r'\.(?:svg|png|webp)',filename):
            raise ValueError('Unsafe logo path')
        data = (ROOT/'web/logos'/filename).read_bytes()
        if len(data)>300000 or hashlib.sha256(data).hexdigest()!=mark.get('sha256'):
            raise ValueError('Logo size or fingerprint mismatch')
        if filename.endswith('.svg'):
            validate_svg(data)
        elif filename.endswith('.png') and not data.startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError('Invalid logo PNG')
        if not all(str(mark.get(k) or '').startswith('https://') for k in ('source_url','image_url')):
            raise ValueError('Logo provenance is missing')


def company_logo(symbol, prefix=''):
    if not re.fullmatch(r'[A-Z0-9]{2,5}', symbol):
        raise ValueError('Unsafe issuer symbol')
    mark = catalog().get(symbol) or {}
    filename = mark.get('filename') or ''
    if filename and not re.fullmatch(re.escape(symbol) + r'\.(?:svg|png|webp)', filename):
        raise ValueError('Unsafe logo path')
    image = (f'<img src="{prefix}logos/{filename}" width="40" height="40" alt="" loading="lazy" decoding="async">'
             if mark.get('status') == 'verified' and filename else '')
    fallback = f'<span class="company-initials" aria-hidden="true">{escape(symbol)}</span>'
    return f'<span class="company-logo{ " is-missing" if not image else ""}" aria-hidden="true">{fallback}{image}</span>'


def logo_credits():
    verified = [r for r in catalog().values() if r.get('status') == 'verified']
    missing = [s for s,r in catalog().items() if r.get('status') != 'verified']
    return ('<details class="panel" id="logos"><summary>Logos des sociétés</summary>'
            f'<p>{len(verified)} identités visuelles documentées et hébergées localement. '
            'Les logos restent la propriété de leurs titulaires ; leur présence n’implique aucun partenariat.</p>'
            '<p>Références publiques : fiches des émetteurs et sites institutionnels. '
            '<a href="company-logos.json">Origine et empreinte de chaque fichier</a>.</p>'
            + (f'<p>Logo non confirmé : {escape(", ".join(missing))}. Le sigle est affiché à la place.</p>' if missing else '')
            + '</details>')
