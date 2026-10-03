import copy
import unittest
from datetime import datetime
from nour.market import CASABLANCA
from nour.overview import update_overview
from nour.market_view import market_panel


class OverviewContracts(unittest.TestCase):
    def setUp(self):
        self.history = {'seances': {'2025-12-31': 20000, '2026-10-02': 17000}}
        self.previous = {'current': {'asof': '2026-10-02'},
                         'last_closed': {'asof': '2026-10-02'}}
        self.row = {'Symbol': 'MASI', 'DateCotation': '05/10/2026 13:45:00',
                    'Cours': 17100, 'CoursVeille': 17000, 'PlusHaut': 17200, 'PlusBas': 16900}

    def test_provisional_index_cannot_become_historical_close(self):
        old = copy.deepcopy(self.history)
        overview, hist = update_overview(self.previous, self.history, [self.row], [],
                                        datetime(2026,10,5,13,45,tzinfo=CASABLANCA))
        self.assertEqual(hist, old)
        self.assertEqual(overview['last_closed']['asof'], '2026-10-02')
        self.assertEqual(overview['current']['status'], 'intraday')
        self.assertNotIn('breadth', overview['current'])
        self.assertEqual(self.previous['current']['asof'], '2026-10-02')

    def test_closed_index_and_ytd_are_dated_and_replayable(self):
        now = datetime(2026,10,5,18,tzinfo=CASABLANCA)
        overview, hist = update_overview(self.previous, self.history, [self.row], [],now)
        self.assertEqual(hist['seances']['2026-10-05'], 17100)
        self.assertEqual(overview['last_closed']['masi']['ytd_pct'], -14.5)
        overview2, hist2 = update_overview(overview, hist, [self.row], [],now)
        self.assertEqual(hist, hist2)
        self.assertEqual(overview, overview2)

    def test_wrong_identity_cancelled_future_regression_and_conflict_rejected(self):
        for mutation in ({'Symbol':'BANK'}, {'DateCotation':'17/09/2026'},
                         {'DateCotation':'06/10/2026'}, {'DateCotation':'01/10/2026'},
                         {'DateCotation':'02/10/2026', 'Cours':18000}, {'Cours':float('nan')}):
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                update_overview(self.previous,self.history,[{**self.row, **mutation}],[],
                                datetime(2026,10,5,18,tzinfo=CASABLANCA))

    def test_summary_cannot_present_other_dates_or_empty_coverage_as_zero(self):
        rows = [{'Symbol': str(i), 'DateDernierCours': '05/10/2026', 'QteEchangee':10,
                 'Volumes':1000, 'VariationP': -1 if i%2 else 1} for i in range(20)]
        rows.append({'Symbol':'OLD','DateDernierCours':'02/10/2026','QteEchangee':999,
                     'Volumes':999999,'VariationP':0})
        overview, _ = update_overview(self.previous,self.history,[self.row],rows,
                                     datetime(2026,10,5,18,tzinfo=CASABLANCA))
        self.assertEqual(overview['current']['breadth'],dict(up=10,down=10,flat=0,quoted=20))
        self.assertEqual(overview['current']['turnover_mad'],20000)
        self.assertNotIn('transactions',overview['current'])

    def test_dated_index_summary_is_preferred_to_subset_aggregation(self):
        row = {**self.row, 'NbrHausse':10, 'NbrBaisse':54, 'NbrInchange':4,
               'NbrValeur':68, 'Volume':258466497.74, 'QteEchange':859537, 'NbrTransaction':5487}
        overview, _ = update_overview(self.previous, self.history, [row], [],
                                     datetime(2026,10,5,18,tzinfo=CASABLANCA))
        current = overview['current']
        self.assertEqual(current['transactions'],5487)
        self.assertEqual(current['breadth']['quoted'],68)
        self.assertEqual(current['turnover_mad'],258466497.74)

    def test_missing_index_has_an_explicit_fallback_and_no_invented_chart(self):
        page = market_panel({'analysis_date':'2026-10-03'})
        self.assertIn('Historique MASI indisponible',page)
        self.assertNotIn('<polyline',page)
        self.assertIn('Bilan de séance indisponible',page)


if __name__ == '__main__':
    unittest.main()
