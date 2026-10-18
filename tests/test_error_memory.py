import copy
import json
import unittest

from nour.error_memory import record_lesson, update_error_memory


class ErrorMemoryContracts(unittest.TestCase):
    def setUp(self):
        self.t1 = '2026-10-18T20:00:00+00:00'
        self.t2 = '2026-10-18T21:00:00+00:00'
        self.change = {'symbol': 'CMGP', 'fields': ['v', 'day_shares', 'day_turnover_mad'],
                       'before': {'candle_shares': 23199, 'day_shares': 23199,
                                  'day_turnover_mad': '6031880.15'},
                       'after': {'candle_shares': 25199, 'day_shares': 25199,
                                 'day_turnover_mad': '6551880.15'}}
        self.failed = {'session': '2026-10-16', 'status': 'unavailable',
                       'proposed_corrections': [self.change],
                       'refusals': [{'reason': 'Second provider missing'}]}
        self.good = {'session': '2026-10-16', 'status': 'reconciled',
                     'publication_safe': True, 'internal_match': True, 'cross_source_verified': True,
                     'providers': [{'source_url': 'https://www.cdgcapitalbourse.ma/api/'},
                                   {'source_url': 'https://www.wafabourse.com/market'}],
                     'validated_symbols': ['CMGP'],
                     'validated_fields': ['v', 'day_shares', 'day_turnover_mad'],
                     'corrections': [self.change]}

    def test_repetitions_are_compacted_and_input_not_mutated(self):
        before = copy.deepcopy(self.failed)
        memory = update_error_memory(None, self.failed, self.t1)
        old = copy.deepcopy(memory)
        result = update_error_memory(memory, self.failed, self.t2)
        self.assertEqual(len(result['entries']), 2)
        self.assertTrue(all(e['occurrences'] == 2 for e in result['entries'].values()))
        self.assertEqual(memory, old)
        self.assertEqual(self.failed, before)
        correction = next(e for e in result['entries'].values() if e['symbol'] == 'CMGP')
        self.assertEqual(correction['before']['day_turnover_mad'], '6031880.15')
        self.assertEqual(correction['after']['day_shares'], 25199)

    def test_outage_never_resolves_but_proven_same_session_does(self):
        memory = update_error_memory(None, self.failed, self.t1)
        self.assertTrue(all(e['status'] == 'open' for e in memory['entries'].values()))
        result = update_error_memory(memory, self.good, self.t2)
        self.assertEqual(len(result['entries']), 2)
        self.assertTrue(all(e['status'] == 'resolved' for e in result['entries'].values()))
        self.assertTrue(all(e['resolution']['evidence'] for e in result['entries'].values()))
        reopened = update_error_memory(result, self.failed, '2026-10-19T20:00:00+00:00')
        self.assertEqual(len(reopened['entries']), 2)
        self.assertTrue(all(e['reopenings'] == 1 for e in reopened['entries'].values()))
        self.assertTrue(all(e['resolved_at'] == self.t2 for e in reopened['entries'].values()))

    def test_status_alone_or_other_session_does_not_resolve(self):
        memory = update_error_memory(None, self.failed, self.t1)
        for changes in ({'cross_source_verified': False}, {'publication_safe': False},
                        {'internal_match': False}, {'providers': []}, {'session': '2026-10-19'}):
            audit = {**self.good, **changes, 'corrections': []}
            result = update_error_memory(memory, audit, self.t2)
            self.assertTrue(all(e['status'] == 'open' for e in result['entries'].values()))

    def test_unvalidated_symbol_or_fields_remain_open(self):
        memory = update_error_memory(None, self.failed, self.t1)
        for changes in ({'validated_symbols': ['ADI']}, {'validated_fields': ['v']}):
            result = update_error_memory(memory, {**self.good, **changes, 'corrections': []}, self.t2)
            cmgp = next(e for e in result['entries'].values() if e['symbol'] == 'CMGP')
            self.assertEqual(cmgp['status'], 'open')

    def test_no_raw_network_errors_credentials_or_nonfinite_values(self):
        change = copy.deepcopy(self.change)
        change['before'].update(token='SECRET', day_turnover_mad=float('nan'))
        audit = {**self.failed, 'proposed_corrections': [change],
                 'refusals': [{'reason': 'HTTP error Authorization: SECRET', 'raw_error': 'SECRET',
                               'evidence': [{'url': 'https://www.wafabourse.com/market?token=SECRET'},
                                            {'url': 'https://SECRET@example.com/'},
                                            {'url': 'https://evil.example/SECRET'}]}]}
        result = update_error_memory(None, audit, self.t1)
        serialized = json.dumps(result, allow_nan=False)
        self.assertNotIn('SECRET', serialized)
        self.assertNotIn('nan', serialized)
        self.assertIn('https://www.wafabourse.com/market', serialized)

    def test_unknown_session_failure_is_retained_not_resolved_later(self):
        memory = update_error_memory(None, {**self.failed, 'session': None}, self.t1)
        result = update_error_memory(memory, self.good, self.t2)
        self.assertTrue(all(e['status'] == 'open' for e in result['entries'].values()
                            if e['session'] is None))

    def test_curated_lessons_are_permanent_and_stable(self):
        lesson = {'id': 'wafa_quantity_is_monetary', 'title': 'Colonne quantité non exploitable',
                  'rule': 'Une colonne répétant les montants ne prouve aucune quantité.',
                  'evidence': [{'url': 'https://www.wafabourse.com/market'}]}
        memory = record_lesson(None, lesson, self.t1)
        result = record_lesson(memory, lesson, self.t2)
        self.assertEqual(len(result['lessons']), 1)
        self.assertEqual(result['lessons'][lesson['id']]['occurrences'], 2)
        self.assertEqual(result['lessons'][lesson['id']]['first_seen'], self.t1)
        self.assertEqual(update_error_memory(result, self.good, self.t2)['lessons'], result['lessons'])

    def test_version_and_undated_resolution_fail_closed(self):
        with self.assertRaises(ValueError):
            update_error_memory({'schema_version': 2}, self.good, self.t1)
        with self.assertRaises(ValueError):
            update_error_memory(None, {**self.good, 'session': None}, self.t1)


if __name__ == '__main__':
    unittest.main()
