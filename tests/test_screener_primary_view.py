from copy import deepcopy
import unittest
from nour.screener_primary_view import review_note


class PrimaryReviewViewTests(unittest.TestCase):
    def test_dated_partial_review_is_escaped_and_does_not_promote_a_claim(self):
        review = {'reviewed_at': '2026-11-09', 'findings': [{'conclusion': '<script>wrong</script>'}]}
        before = deepcopy(review)
        html = review_note(review, '2026-11-09')
        self.assertIn('revue limitée', html)
        self.assertIn('screener-primary-review.json', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>', html)
        self.assertEqual(review, before)

    def test_future_or_invalid_review_is_not_presented_as_past_evidence(self):
        self.assertEqual(review_note({'reviewed_at': '2026-11-09'}, '2026-11-08'), '')
        self.assertEqual(review_note({'reviewed_at': None}, '2026-11-09'), '')
