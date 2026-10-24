"""Extract the configured issuer batch; a source failure preserves other issuers."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from nour.sector_ingestion import collect
from nour.market import atomic_json

def main():
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,default=ROOT/'.cache/sector-pdf');args=p.parse_args()
    path=ROOT/'data/sector_disclosures.json'
    config=json.loads((ROOT/'knowledge/sector_extraction_profiles.json').read_text())
    previous=json.loads(path.read_text()) if path.exists() else {}
    discovery=ROOT/'data/official_document_candidates.json'
    state=collect(config,previous,json.loads(discovery.read_text()) if discovery.exists() else {},args.cache)
    atomic_json(path,state)
    print(json.dumps(dict(records=sum(len(c['records']) for c in state['catalogues'].values()),
        health=state['health'],candidates=len(state['candidates'])),ensure_ascii=False))
if __name__=='__main__':main()
