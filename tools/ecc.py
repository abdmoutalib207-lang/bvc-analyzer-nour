"""Install/verify the pinned ECC subset inside this repository only, offline."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / 'vendor/ecc'


def expected_links(manifest):
    links = {}
    for entry in manifest['files']:
        p = Path(entry['path'])
        if p.parts[0] == 'skills':
            name = p.parts[1]
            for runtime in ('.agents', '.claude'):
                links[f'{runtime}/skills/ecc-{name}'] = VENDOR / 'skills' / name
        elif p.parts[0] == 'agents':
            links[f'.claude/agents/ecc-{p.name}'] = VENDOR / p
    return links


def verify_sources(manifest):
    if manifest['repository'] != 'https://github.com/affaan-m/ECC':
        raise ValueError('Unexpected ECC repository')
    if len(manifest['commit']) != 40:
        raise ValueError('ECC commit must be pinned')
    for entry in manifest['files']:
        path = Path(entry['path'])
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('Unsafe manifest path')
        source = VENDOR / path
        if source.is_symlink() or not source.is_file():
            raise ValueError(f'Missing original: {path}')
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if digest != entry['sha256']:
            raise ValueError(f'ECC original changed: {path}')


def run(install=False):
    manifest = json.loads((VENDOR/'manifest.json').read_text())
    verify_sources(manifest)
    for relative, target in expected_links(manifest).items():
        link = ROOT / relative
        if install and not link.exists() and not link.is_symlink():
            link.parent.mkdir(parents=True, exist_ok=True)
            import os
            link.symlink_to(os.path.relpath(target, link.parent), target_is_directory=target.is_dir())
        if not link.is_symlink() or link.resolve() != target.resolve():
            raise ValueError(f'Unexpected ECC binding: {relative}; refusing overwrite')
    print(f"ECC {manifest['commit'][:12]} : {manifest['skill_count']} skills, "
          f"{manifest['agent_count']} review profiles, originals and local bindings verified")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['install', 'verify'])
    run(parser.parse_args().action == 'install')
