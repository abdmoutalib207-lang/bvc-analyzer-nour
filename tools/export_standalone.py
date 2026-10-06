"""Bundle the generated Nour site into one offline HTML with all local links."""
import argparse
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def export(target):
    web = ROOT / 'web'
    report = json.loads((web / 'report.json').read_text(encoding='utf-8'))
    paths = ['index.html', 'briefing.html', 'actualites.html']
    paths += [f'titres/{r["symbol"]}.html' for r in report['results']]
    paths += [f'historique/{r["symbol"]}.csv' for r in report['results']]
    paths += ['report.json', 'news.json', 'briefing.json']
    files = {p: (web / p).read_text(encoding='utf-8') for p in paths}
    # Preserve the existing offline bundle: the new online assistant assets
    # are external files, not resources this exporter currently embeds.
    for path in paths:
        if path.endswith('.html'):
            files[path] = re.sub(r'<link rel="stylesheet" href="(?:\.\./)?assistant\.css">', '', files[path])
            files[path] = re.sub(r'<script src="(?:\.\./)?assistant\.js" defer></script>', '', files[path])
            files[path] = re.sub(r'<button hidden type="button" id="assistant-open".*?</dialog>', '', files[path], flags=re.DOTALL)
    payload = json.dumps(files, ensure_ascii=False).replace('<', '\\u003c')
    options = ''.join(f'<option value="titres/{html.escape(r["symbol"])}.html">'
                      f'{html.escape(r["symbol"])} — {html.escape(r["name"])}</option>'
                      for r in report['results'])
    shell = '''<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BVC Analyzer Nour — application complète hors ligne</title>
<style>body{margin:0;background:#08121b;color:#e7eeed;font:14px system-ui}
header{padding:10px 16px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;border-bottom:1px solid #36515b}
header a{color:#b4e283}select{max-width:100%;padding:8px;background:#142933;color:#e7eeed;border:1px solid #36515b;border-radius:6px}
small{color:#c6d1d5}iframe{border:0;width:100%;height:calc(100dvh - 105px);min-height:420px;display:block}
#error{color:#ffc2b2;padding:8px}#error:empty{display:none}</style></head><body>
<header><strong>BVC Analyzer Nour · 80 titres</strong>
<a href="#index.html">Marché</a><a href="#briefing.html">Briefing</a><a href="#actualites.html">Actualités</a>
<label>Ouvrir un titre <select id="ticker"><option value="index.html">Les 80 valeurs</option>__OPTIONS__</select></label>
<small>Copie hors ligne · données du __DATE__ · aucune actualisation réseau des cours</small></header>
<p id="error" role="status"></p>
<noscript>Activez JavaScript pour naviguer entre les fiches dans ce fichier unique.</noscript>
<iframe id="app" title="Marché — BVC Analyzer Nour" srcdoc="__HOME__"></iframe>
<script id="bundle" type="application/json">__PAYLOAD__</script>
<script>
(() => {
  const files=JSON.parse(document.getElementById('bundle').textContent);
  const frame=document.getElementById('app'), select=document.getElementById('ticker');
  let current='index.html';
  const show=()=>{
    let path;
    try {path=decodeURIComponent(location.hash.slice(1)) || 'index.html';} catch {path='index.html';}
    if(!Object.hasOwn(files,path) || !path.endsWith('.html')) path='index.html';
    current=path; select.value=path.startsWith('titres/')?path:'index.html';
    frame.title=path.startsWith('titres/')?path.slice(7,-5)+' — BVC Analyzer Nour':'BVC Analyzer Nour';
    frame.srcdoc=files[path];
  };
  frame.addEventListener('load',()=>{
    const doc=frame.contentDocument;
    if(!doc) return;
    doc.addEventListener('click',event=>{
      const link=event.target.closest('a[href]');
      if(!link) return;
      const raw=link.getAttribute('href');
      if(!raw || raw.startsWith('#') || /^[a-z][a-z0-9+.-]*:/i.test(raw)) return;
      const url=new URL(raw,'https://nour.invalid/'+current);
      if(url.origin!=='https://nour.invalid') return;
      event.preventDefault();
      const path=decodeURIComponent(url.pathname.slice(1));
      if(!Object.hasOwn(files,path)) {document.getElementById('error').textContent='Ressource absente de cette copie : '+path;return;}
      if(path.endsWith('.html')) {location.hash=path;return;}
      const objectUrl=URL.createObjectURL(new Blob([files[path]],{type:path.endsWith('.csv')?'text/csv;charset=utf-8':'application/json'}));
      const download=document.createElement('a'); download.href=objectUrl; download.download=path.split('/').pop();
      download.click(); setTimeout(()=>URL.revokeObjectURL(objectUrl),1000);
    });
  });
  select.addEventListener('change',()=>{location.hash=select.value;});
  addEventListener('hashchange',show); show();
})();
</script></body></html>'''
    output = shell.replace('__OPTIONS__', options).replace('__DATE__', html.escape(report['snapshot_updated'][:10]))
    output = output.replace('__HOME__', html.escape(files['index.html'], quote=True)).replace('__PAYLOAD__', payload)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(output, encoding='utf-8')
    print(f'{target}: {len(report["results"])} fiches, {len(paths)} ressources embarquées')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    export(parser.parse_args().output)
