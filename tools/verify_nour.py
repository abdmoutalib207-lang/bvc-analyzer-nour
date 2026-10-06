"""Executable ECC verification adapted to Nour's actual Python/JS toolchain."""
import argparse
from datetime import date
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--asof', default=date.today().isoformat())
    args = parser.parse_args()
    commands = [[sys.executable, 'tools/ecc.py', 'verify']]
    if args.build:
        commands.append([sys.executable, 'run.py', '--asof', args.asof, '--slot', 'refresh'])
    commands.append([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'])
    commands.extend(['node', '--check', f'web/{name}.js'] for name in
                    ('nour', 'chart', 'chart-controls', 'market', 'research', 'assistant'))
    commands.extend(['node', f'tools/{name}.cjs'] for name in
                    ('test_research', 'test_chart_controls', 'test_news_filters', 'test_assistant'))
    commands.append([sys.executable, 'tools/audit_site.py'])
    commands.append([sys.executable, 'tools/audit_readiness.py'])
    for command in commands:
        subprocess.run(command, cwd=ROOT, check=True)
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    print('Nour gate PASS. Type analysis, coverage percentage, full accessibility '
          'and live LLM provider: not measured by this gate.')


if __name__ == '__main__':
    main()
