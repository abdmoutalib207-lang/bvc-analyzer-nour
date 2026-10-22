"""Collection clocks preserve the observation date and distinguish failed attempts."""
from datetime import datetime
import unittest
from nour.collection_view import collection_stamp
from nour.issuer_view import issuer_heading
from nour.runtime import ZONE


class CollectionTime(unittest.TestCase):
    def test_zoned_observation_uses_casablanca_and_preserves_date_rollover(self):
        for source in ('2026-02-20T23:45:00+00:00', '2026-10-19T23:45:00Z'):
            expected=datetime.fromisoformat(source.replace('Z','+00:00')).astimezone(ZONE)
            text=collection_stamp(source)
            self.assertIn(expected.strftime('%d/%m/%Y à %Hh%M'),text)
            self.assertIn(f'datetime="{expected.isoformat()}"',text)
            self.assertIn('Casablanca',text)

    def test_missing_invalid_or_naive_time_never_uses_build_time(self):
        for value in (None,'','invalid','2026-10-19T15:30:00','<script>'):
            self.assertEqual(collection_stamp(value),'<p class="collection-stamp">Heure de collecte non communiquée.</p>')

    def test_failed_attempt_does_not_claim_a_new_close(self):
        item={'symbol':'ADI','asof':'2026-10-16','price':360,'decision':'OBSERVABLE'}
        text=issuer_heading(item,{'name':'Alliances','candles':[]},
                            {'checked_at':'2026-10-19T15:30:00Z','result':'error'})
        self.assertIn('Dernière tentative de collecte',text)
        self.assertIn('datetime="2026-10-16">16/10/2026',text)
        self.assertIn('Clôture disponible',text)
        self.assertIn('data-quote-mode="close"',text)
        self.assertNotIn('Cotation : <time datetime="2026-10-19',text)
