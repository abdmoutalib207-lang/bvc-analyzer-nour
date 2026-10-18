"""The screener/export copies canonical outputs, including absent and zero values."""
import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest

from nour.fundamental_view import rows, panel, export_csv

ROOT=Path(__file__).resolve().parents[1]


class FundamentalExplorer(unittest.TestCase):
    def test_every_exported_ratio_and_reservation_matches_the_report(self):
        report=json.loads((ROOT/'web/report.json').read_text())
        original=copy.deepcopy(report)
        output=rows(report)
        self.assertEqual(len(output),80)
        for source,row in zip(report['results'],output):
            for key in ('eps_mad','pe','pb','roe_pct','warnings'):
                self.assertEqual(row[key],source['fundamental'].get(key))
            self.assertEqual(row['price_date'],source.get('asof'))
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'fundamentaux.csv';export_csv(report,path)
            with path.open(encoding='utf-8-sig') as stream:
                data=list(csv.DictReader(stream,delimiter=';'))
            self.assertEqual(len(data),80)
            for row in data:
                canonical=next(r for r in output if r['symbol']==row['symbol'])
                if canonical['eps_mad'] is None:self.assertEqual(row['eps_mad'],'')
                self.assertEqual(row['warnings'],' | '.join(canonical['warnings']))
        self.assertEqual(report,original)

    def test_no_missing_number_or_nonfinite_value_becomes_zero(self):
        report={'results':[{'symbol':'AAA','name':'A < B','fundamental':{'eps_mad':0,'pe':None,'pb':float('inf'),'roe_pct':-5}}]}
        r=rows(report)[0]
        self.assertEqual(r['eps_mad'],0)
        self.assertIsNone(r['pe']);self.assertIsNone(r['pb'])
        self.assertEqual(r['roe_pct'],-5)
        text=panel(report)
        self.assertIn('Indisponible',text)
        self.assertNotIn('Infinity',text)


if __name__=='__main__':
    unittest.main()
