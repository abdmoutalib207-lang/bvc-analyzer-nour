"""Fail before workflow mutations unless both GitHub and git target Nour."""
import os
from pathlib import Path
import subprocess
from urllib.parse import urlsplit

ALLOWED='abdmoutalib207-lang/bvc-analyzer-nour'


def check_scope(repository, remote):
    if repository and repository!=ALLOWED:raise ValueError('GitHub repository outside authorized Nour scope')
    if remote.startswith('git@github.com:'):target=remote.split(':',1)[1]
    else:
        parsed=urlsplit(remote)
        if parsed.hostname!='github.com':raise ValueError('Remote host outside authorized scope')
        target=parsed.path.lstrip('/')
    if target.removesuffix('.git')!=ALLOWED:raise ValueError('Remote repository outside authorized Nour scope')
    return True

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    remote=subprocess.check_output(['git','config','--get','remote.origin.url'],cwd=root,text=True).strip()
    check_scope(os.environ.get('GITHUB_REPOSITORY'),remote)
    print('Authorized write scope: '+ALLOWED+'; principal engine read-only.')
