"""Record the exact post-save artifact commit, without self-referential Git data."""
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nour.publication import publication_manifest


if __name__ == '__main__':
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    manifest = publication_manifest(ROOT/'web', commit, os.environ.get('GITHUB_RUN_ID', ''),
                                    datetime.now(timezone.utc).isoformat())
    (ROOT/'web/publication.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Publication artifact identity recorded for ' + commit)
