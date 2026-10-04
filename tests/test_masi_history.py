import copy
import json
import unittest
from pathlib import Path

from nour.masi_history import extend_history


class MasiHistoryExtension(unittest.TestCase):
    def setUp(self):
        self.original = {'seances': {'2025-12-31': 100.0, '2026-10-02': 150.0},
                         'provenance': {'cancelled_sessions': [{'date': '2026-09-17'}]}}

    def test_extension_preserves_existing_values_and_replays_without_new_audit(self):
        source = {'seances': {'2023-01-02': 90, '2025-12-31': 100.005}}
        before = copy.deepcopy(self.original)
        result = extend_history(self.original, source, {'commit': 'pinned'}, '2026-10-04')
        self.assertEqual(self.original, before)
        self.assertEqual(result['seances']['2025-12-31'], 100)
        self.assertEqual(result['seances']['2026-10-02'], 150)
        self.assertEqual(result['provenance']['cancelled_sessions'], before['provenance']['cancelled_sessions'])
        self.assertEqual(list(result['seances']), sorted(result['seances']))
        self.assertEqual(extend_history(result, source, {'commit': 'pinned'}, '2026-10-04'), result)

    def test_divergence_rejects_the_entire_extension(self):
        before = copy.deepcopy(self.original)
        with self.assertRaisesRegex(ValueError, 'divergente'):
            extend_history(self.original, {'seances': {'2023-01-02': 90, '2025-12-31': 101}}, {}, '2026-10-04')
        self.assertEqual(self.original, before)

    def test_invalid_values_future_weekend_and_cancelled_sessions_are_rejected(self):
        for day, value in [('2023-01-02', True), ('2023-01-02', float('nan')),
                           ('2023-01-02', -1), ('2023-01-01', 100),
                           ('2026-10-05', 100), ('2026-09-17', 100)]:
            with self.subTest(day=day, value=value), self.assertRaises(ValueError):
                extend_history(self.original, {'seances': {day: value}}, {}, '2026-10-04')

    def test_published_fixture_keeps_the_complete_dated_extension(self):
        root = Path(__file__).resolve().parents[1]
        history = json.loads((root / 'data/masi_history.json').read_text())
        self.assertGreaterEqual(len(history['seances']), 916)
        self.assertEqual(min(history['seances']), '2023-01-02')
        self.assertEqual(history['seances']['2023-01-02'], 10709.14)
        self.assertNotIn('2026-09-17', history['seances'])
        audit = history['provenance']['history_extensions'][0]
        self.assertEqual((audit['added'], audit['common_sessions']), (719, 197))
        self.assertEqual(audit['max_common_delta_points'], 0)
        self.assertTrue(audit['existing_closes_preserved'])
