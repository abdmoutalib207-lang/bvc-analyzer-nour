"""Serve existing Nour pages and its optional, explicitly configured local LLM."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nour.assistant_server import serve

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    serve(ROOT/'web', parser.parse_args().port)
