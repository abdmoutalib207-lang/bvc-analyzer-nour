"""Run the complete browser suite on an isolated, deliberately invalid ADI feed.

All synthetic observations stay in a TemporaryDirectory. Nothing is copied back
into data/ or web/, and no remote publication or API write occurs.
"""
import argparse
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from threading import Thread
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'tests'))
import run
from nour.market import atomic_json
from nour.publication import publication_manifest
from nour.volume_guard import reconcile_volumes
from test_local_market import universe, NOW


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def prepare(root, inputs):
    shutil.copytree(ROOT/'data', root/'data')
    shutil.copytree(ROOT/'web', root/'web')
    fixture, proof = reconcile_volumes(*inputs, now=NOW, allow_local_isolation=True)
    atomic_json(root/'data/market_snapshot.json', fixture)
    proof['validated_snapshot_sha256'] = hashlib.sha256((root/'data/market_snapshot.json').read_bytes()).hexdigest()
    for provider, payload in zip(proof['providers'], [inputs[1], inputs[3]]):
        provider['raw_sha256'] = hashlib.sha256(json.dumps(payload).encode()).hexdigest()
    atomic_json(root/'data/market_integrity.json', proof)
    atomic_json(root/'data/market_overview.json', {'current':inputs[2], 'last_closed':inputs[2]})
    atomic_json(root/'data/issuer_status.json', {'observed_asof':'2026-10-23', 'records':{}})
    commit = subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip()
    # Keep a genuine code identity while isolating GitHub's scheduled-run env.
    with patch.object(run, 'ROOT', root), patch.dict(os.environ, {'NOUR_CODE_COMMIT':commit}, clear=True):
        run._build(argparse.Namespace(asof='2026-10-23', slot='refresh'), root/'web')
    manifest=publication_manifest(root/'web', commit)
    atomic_json(root/'web/publication.json', manifest)
    report=json.loads((root/'web/report.json').read_text())
    assert manifest['generator_commit']==report['runtime']['commit']==commit
    assert ('data-generator="'+commit+'"') in (root/'web/index.html').read_text()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-only', action='store_true', help='Check generation/79 parity without Chromium')
    args = parser.parse_args()
    # The same fixed synthetic source universe used by the Python stress tests.
    with tempfile.TemporaryDirectory(prefix='nour-browser-stress-') as d:
        root=Path(d)
        healthy_inputs=universe()
        healthy=prepare(root/'healthy', healthy_inputs)
        broken_inputs=universe()
        next(r for r in broken_inputs[3]['rows'] if r['symbol']==broken_inputs[4]['ADI'])['shares'] += 1
        partial_report=prepare(root/'quarantined', broken_inputs)
        before={r['symbol']:r for r in healthy['results']}
        after={r['symbol']:r for r in partial_report['results']}
        assert set(before)==set(after) and len(after)==80
        assert partial_report['cross_source_volume_audit']['quarantined_symbols']==['ADI']
        assert after['ADI']['price'] is None and after['ADI']['technical']['sma50'] is None
        assert after['ADI']['fundamental']['pe'] is None
        for symbol in sorted(set(after)-{'ADI'}):
            for key in ('technical','fundamental','canonical_score'):
                assert before[symbol][key]==after[symbol][key], (symbol,key)
            relative=Path('historique')/(symbol+'.csv')
            assert (root/'healthy/web'/relative).read_bytes()==(root/'quarantined/web'/relative).read_bytes(), symbol
        print('Browser stress fixture: ADI invalid, 79 technical/fundamental/scores and CSVs identical.', flush=True)
        if args.prepare_only:
            return
        handler=partial(QuietHandler, directory=str(root/'quarantined/web'))
        server=ThreadingHTTPServer(('127.0.0.1',0), handler)
        thread=Thread(target=server.serve_forever, daemon=True)
        thread.start()
        env=dict(os.environ)
        if env.get('NOUR_SCREENSHOTS'):
            env['NOUR_SCREENSHOTS']=str(Path(env['NOUR_SCREENSHOTS'])/'quarantined')
        try:
            subprocess.run(['node',str(ROOT/'tools/test_assistant_browser.cjs'),
                            f'http://127.0.0.1:{server.server_port}/'],cwd=ROOT,env=env,check=True)
        finally:
            server.shutdown();server.server_close();thread.join(timeout=5)
        print('Quarantined browser stress PASS: 80 pages, 79 preserved, no invalid ADI price/PER/MM50.', flush=True)


if __name__=='__main__':
    main()
