import copy
import io
import json
import unittest

from nour.secondary_market import ACTION, fetch_wafabourse, parse_wafabourse


OBSERVED = '2026-10-18T20:00:00+00:00'


def fixture():
    return [{ACTION: {'Valid': True, 'Data': [
        {'Symbol': 'ADI', 'IdTypeValeur': 1, 'Etat': 'Market Close',
         'Cours': 360, 'Volumes': 3237243.95, 'QteEchangee': 9132,
         'DateDernierCours': '16/10/2026 15:30:34'},
        {'Symbol': 'AFM', 'IdTypeValeur': 1, 'Etat': 'Market Close',
         'Cours': '', 'Volumes': '', 'QteEchangee': '', 'DateDernierCours': ''},
    ]}}]


class SecondaryMarketTests(unittest.TestCase):
    def parse(self, data):
        return parse_wafabourse(data, observed_at=OBSERVED, expected_session='2026-10-16')

    def test_explicit_trade_date_and_units(self):
        result = self.parse(fixture())
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['session'], '2026-10-16')
        self.assertTrue(result['market_closed'])
        self.assertEqual(result['rows'], [dict(symbol='ADI', session='2026-10-16',
                                               price=360, amount_mad=3237243.95, shares=9132)])

    def test_invalid_source_cannot_produce_partial_total(self):
        for field, values in {
            'Volumes': [float('nan'), float('inf'), '1e1000', -1, True, ''],
            'Cours': [0, -2, False, 'NaN'],
            'QteEchangee': [1.5, -2, float('inf'), True],
            'DateDernierCours': ['', '2026-10-16', '31/02/2026 10:00:00',
                                 '18/10/2026 10:00:00', '19/10/2026 10:00:00'],
            'Symbol': ['', None, 'ADI/../../'],
            'IdTypeValeur': [2, '1', None, True],
        }.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    data = fixture()
                    data[0][ACTION]['Data'][0][field] = value
                    result = self.parse(data)
                    self.assertEqual(result['status'], 'invalid')
                    self.assertEqual(result['rows'], [])

    def test_duplicate_old_session_and_action_refused(self):
        data = fixture()
        data[0][ACTION]['Data'].append(copy.deepcopy(data[0][ACTION]['Data'][0]))
        self.assertEqual(self.parse(data)['status'], 'invalid')
        data = fixture()
        data[0][ACTION]['Data'][0]['DateDernierCours'] = '15/10/2026 15:30:34'
        self.assertEqual(self.parse(data)['status'], 'invalid')
        for payload in ({}, [], [{'OTHER': {'Valid': True, 'Data': []}}],
                        [{ACTION: {'Valid': 'true', 'Data': []}}]):
            self.assertEqual(self.parse(payload)['status'], 'invalid')

    def test_pdf_like_quantity_not_claimed_as_shares(self):
        data = fixture()
        data[0][ACTION]['Data'][0]['Volumes'] = 100
        data[0][ACTION]['Data'][0]['QteEchangee'] = 100
        result = self.parse(data)
        self.assertEqual(result['status'], 'ok')
        self.assertIsNone(result['rows'][0]['shares'])
        data[0][ACTION]['Data'][0].pop('QteEchangee')
        self.assertIsNone(self.parse(data)['rows'][0]['shares'])

    def test_intraday_flag_and_mixed_sessions(self):
        data = fixture()
        data[0][ACTION]['Data'][0]['Etat'] = 'Trading'
        self.assertFalse(self.parse(data)['market_closed'])
        extra = copy.deepcopy(data[0][ACTION]['Data'][0])
        extra.update(Symbol='IAM', DateDernierCours='15/10/2026 15:00:00')
        data[0][ACTION]['Data'].append(extra)
        self.assertEqual(self.parse(data)['status'], 'invalid')

    def test_transport_matches_frontend_and_does_not_leak_token(self):
        class Opener:
            def __init__(self):
                self.requests = []

            def open(self, request, timeout):
                self.requests.append((request, timeout))
                payload = {'token': 'transient-token-test'} if len(self.requests) == 1 else fixture()
                return io.BytesIO(json.dumps(payload).encode())

        opener = Opener()
        result = fetch_wafabourse(opener=opener, observed_at=OBSERVED,
                                 expected_session='2026-10-16', timeout=100)
        self.assertEqual(result['status'], 'ok')
        first, second = opener.requests
        self.assertEqual(first[0].full_url, 'https://www.wafabourse.com/api/proxy/token')
        self.assertEqual(second[0].full_url, 'https://www.wafabourse.com/api/proxy/data/JNNJ')
        self.assertEqual(second[0].get_method(), 'POST')
        self.assertEqual(second[0].headers['X-proxy-token'], 'transient-token-test')
        self.assertEqual(json.loads(second[0].data)['ACTIONS'][0]['PARAMS'][0]['VALUE'], 1)
        self.assertEqual(first[1], 15)
        self.assertNotIn('transient-token-test', json.dumps(result))

    def test_network_failure_is_explicit_bounded_and_not_secret_output(self):
        class FailingOpener:
            def open(self, request, timeout):
                raise OSError('private-network-details')

        result = fetch_wafabourse(opener=FailingOpener(), observed_at=OBSERVED)
        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(result['rows'], [])
        self.assertNotIn('private-network-details', json.dumps(result))


if __name__ == '__main__':
    unittest.main()
