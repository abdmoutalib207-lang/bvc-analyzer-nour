import copy
import json
from pathlib import Path
import unittest
from nour.volume_history import checked_history, compare_current, history_page


class VolumeHistory(unittest.TestCase):
    def setUp(self):
        self.doc=json.loads((Path(__file__).resolve().parents[1]/'data/volume_history.json').read_text())
        self.market={'asof':'2026-10-19','turnover_mad':113956983.12,'shares':876356,
                     'transactions':None,'transactions_reported':2851}

    def test_export_keeps_dates_segments_and_exact_cents(self):
        checked=checked_history(self.doc)
        rows=checked['records']
        self.assertEqual(len(rows),38)
        central={r['session']:r for r in rows if r['market']=='Marché central'}
        self.assertEqual(len(central),21)
        self.assertEqual(central['2026-10-16']['transactions'],3114)
        self.assertEqual(central['2026-10-12']['turnover_mad'],'52945136.05')
        self.assertEqual(central['2026-10-19']['transactions'],3671)
        checked['records'].clear()
        self.assertEqual(len(self.doc['records']),38)

    def test_counter_difference_does_not_overwrite_sources_or_claim_detail_match(self):
        before=copy.deepcopy(self.market)
        result=compare_current(self.doc,self.market)
        self.assertEqual(result['status'],'difference')
        self.assertEqual(result['differences'],{'transactions':{'observed':2851,'export':3671}})
        self.assertEqual(self.market,before)
        self.assertNotIn('publication_safe',result)
        self.assertIn('in!A2:E2',history_page(self.doc,result))

    def test_no_previous_session_fallback_and_no_transfers_in_central_sum(self):
        self.market.update(asof='2026-10-20')
        self.assertEqual(compare_current(self.doc,self.market)['status'],'not_covered')
        self.market.update(asof='2026-10-16',turnover_mad=117005677.43,shares=506826,transactions_reported=3114)
        self.assertEqual(compare_current(self.doc,self.market)['status'],'matched')

    def test_bad_provenance_duplicates_or_numeric_inputs_are_refused(self):
        changes=[{'transactions':True},{'shares':-1},{'row':1},{'session':'2026-02-30'},
                 {'market':'Tous marchés'},{'turnover_mad':'NaN'},{'turnover_mad':'1.001'}]
        for change in changes:
            doc=copy.deepcopy(self.doc);doc['records'][0].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):
                checked_history(doc)
        doc=copy.deepcopy(self.doc);doc['records'].append(doc['records'][0])
        with self.assertRaises(ValueError):checked_history(doc)
        doc=copy.deepcopy(self.doc);doc['source']['sha256']='bad'
        with self.assertRaises(ValueError):checked_history(doc)
