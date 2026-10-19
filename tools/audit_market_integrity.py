"""Last independent gate: no complete-close publication with incoherent totals."""
import json
import argparse
from pathlib import Path
import sys
from decimal import Decimal
from urllib.parse import urlsplit
from urllib.request import Request,urlopen
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nour.report_contracts import volume_reconciliation
from nour.market_integrity import validated_detail_scope


def audit_market_integrity(report):
    overview=report.get('market_overview') or {}
    internal=volume_reconciliation(report,overview)
    cross=report.get('cross_source_volume_audit') or {}
    detail_valid=validated_detail_scope(report,cross)
    failures=[]
    if overview.get('status')=='closed' and internal['status']!='matched' and not detail_valid:
        failures.append('Les montants, quantités ou lignes de la clôture ne retrouvent pas le total daté.')
    if cross.get('status') in ('conflict','incomplete','stale') or cross.get('publication_safe') is False:
        failures.append('Rapprochement externe contradictoire ou non applicable à ce snapshot.')
    claimed=cross.get('status') in ('matched','reconciled') or cross.get('cross_source_verified')
    if claimed and (cross.get('publication_safe') is not True or cross.get('cross_source_verified') is not True
            or cross.get('internal_match') is not True or (internal['status']!='matched' and not detail_valid)
            or cross.get('session')!=overview.get('asof')
            or cross.get('validated_snapshot_sha256')!=(report.get('provenance') or {}).get('market_snapshot_sha256')):
        failures.append('Statut multisource sans preuve cohérente pour cette version.')
    if claimed:
        try:
            after=cross['totals']['retained_after'];second=cross['totals']['secondary']
            if (abs(Decimal(str(after['turnover_mad']))-Decimal(str(internal['lines_turnover_mad'])))>Decimal('.01')
                    or after['shares']!=internal['lines_shares'] or after['quoted']!=internal['observed_lines']
                    or abs(Decimal(str(second['turnover_mad']))-Decimal(str(after['turnover_mad'])))>Decimal('.01')
                    or second['quoted']!=after['quoted']):
                failures.append('Les totaux attestés ne correspondent pas au rapport exporté.')
            if cross.get('quantities_cross_source_verified') and second['shares']!=after['shares']:
                failures.append('Quantités présentées comme recoupées sans agrégats concordants.')
            providers=cross['providers']
            hosts={urlsplit(p['source_url']).hostname for p in providers if len(p.get('raw_sha256',''))==64}
            if len(hosts)<2 or None in hosts:
                failures.append('Deux fournisseurs et leurs empreintes ne sont pas identifiés.')
        except (KeyError,TypeError,ValueError,ArithmeticError):
            failures.append('Preuve de rapprochement incomplète.')
    if cross.get('publication_scope')=='validated_title_lines' and not detail_valid:
        failures.append('La preuve de publication limitée aux lignes est invalide.')
    return {'status':'blocked' if failures else 'checked_with_reservations' if detail_valid else 'checked','failures':failures,
            'internal':internal,'cross_source_status':cross.get('status','not_observed')}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--public',action='store_true')
    parser.add_argument('--generator-commit')
    args=parser.parse_args()
    if args.public:
        with urlopen(Request('https://abdmoutalib207-lang.github.io/bvc-analyzer-nour/report.json',
                             headers={'User-Agent':'Nour-publication-integrity-check'}),timeout=25) as response:
            report=json.load(response)
    else:
        report=json.loads((Path(__file__).resolve().parents[1]/'web/report.json').read_text())
    result=audit_market_integrity(report)
    if args.generator_commit and (report.get('provenance') or {}).get('generator_commit')!=args.generator_commit:
        result['failures'].append('La page réellement servie ne correspond pas au générateur attendu.')
        result['status']='blocked'
    print(json.dumps(result,ensure_ascii=False));sys.exit(bool(result['failures']))
