from copy import deepcopy
import unittest
from nour.diagnostics import update_journal
from nour.resilience import issue

class DiagnosticTests(unittest.TestCase):
    def row(self):return dict(symbol='ADI',name='Alliances',decision='OBSERVABLE',price=300,quality={'issues':[]},technical={'sma20':300})
    def test_history_first_detection_persistence_resolution_and_reopening(self):
        row=self.row();issue(row,'technical','injected','Calcul impossible',['technical.sma20']);row['technical']['sma20']=None
        report={'results':[row]};one=update_journal(None,report,'2026-10-23T10:00:00+01:00')
        key=next(iter(one['entries']));two=update_journal(one,report,'2026-10-23T11:00:00+01:00')
        self.assertEqual(two['entries'][key]['first_seen'],one['entries'][key]['first_seen'])
        self.assertEqual(two['entries'][key]['state'],'persistent')
        unchanged=update_journal(two,report,'2026-10-23T11:00:00+01:00')
        self.assertEqual(unchanged['entries'][key]['occurrences'],2)
        resolved=update_journal(two,{'results':[self.row()]},'2026-10-23T12:00:00+01:00')
        self.assertEqual(resolved['entries'][key]['state'],'resolved')
        reopened=update_journal(resolved,report,'2026-10-23T13:00:00+01:00')
        self.assertEqual(len(reopened['entries'][key]['resolutions']),1)
        self.assertEqual(reopened['entries'][key]['state'],'new')

    def test_failed_source_or_missing_observation_never_resolves_price(self):
        row=self.row();issue(row,'price','source_conflict','Donnée contradictoire',['price'])
        state=update_journal(None,{'results':[row]},'2026-10-23T10:00:00+01:00')
        next_report={'results':[self.row()],'health':{'result':'error','message':'Source inaccessible'}}
        state=update_journal(state,next_report,'2026-10-23T11:00:00+01:00')
        local=next(x for x in state['entries'].values() if x['symbol']=='ADI')
        self.assertNotEqual(local['state'],'resolved')
        next_report['results'][0].update(source_checked_at='2026-10-23T12:00:00+01:00',price_validated_at='2026-10-23T12:00:00+01:00')
        state=update_journal(state,next_report,'2026-10-23T12:01:00+01:00')
        local=next(x for x in state['entries'].values() if x['symbol']=='ADI');self.assertEqual(local['state'],'resolved')
