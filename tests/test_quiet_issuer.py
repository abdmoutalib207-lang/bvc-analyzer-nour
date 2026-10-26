"""Progressive disclosure keeps material caveats and missing values legible."""
from copy import deepcopy
from html.parser import HTMLParser
import unittest
from nour.issuer_view import issuer_snapshot
from nour.sector_view import quality_card, sector_card

class Tags(HTMLParser):
    def __init__(self):super().__init__();self.details=[]
    def handle_starttag(self,tag,attrs):
        if tag=='details':self.details.append(dict(attrs))

class QuietIssuerTests(unittest.TestCase):
    def test_snapshot_uses_existing_annual_outputs_and_flags_unresolved_debt(self):
        row={'asof':'2026-10-23','decision':'OBSERVABLE','fundamental':{
            'exercise':2025,'pe':None,'pb':0,'earnings_mmad':-10,'roe_pct':-2,
            'warnings':['Changement de reconnaissance du CA : pas à méthode constante'],
            'debt_reconciliation':{'status':'unresolved'}}}
        before=deepcopy(row);page=issuer_snapshot(row)
        self.assertEqual(row,before)
        for text in ('Non significatif','0,00','-10,00','Comparabilité comptable','Dette publiée','2025','23/10/2026'):
            self.assertIn(text,page)
        self.assertEqual(page.count('class="issuer-keyfigure"'),4)
        self.assertNotIn('1 303',page) # no fallback from an unrelated published measure

    def test_unknown_nonfinite_and_bool_are_not_zero(self):
        page=issuer_snapshot({'fundamental':{'pe':float('nan'),'pb':True}})
        self.assertEqual(page.count('<strong>—</strong>'),4)
        self.assertNotIn('0,00',page)

    def test_diagnostics_are_closed_but_suspension_notice_is_visible(self):
        row={'symbol':'DIS','decision':'SUSPENDU','fundamental':{},'quality':{'issues':['Historique absent']}}
        self.assertIn('suspendu',issuer_snapshot(row))
        p=Tags();p.feed(quality_card(row));self.assertEqual(len(p.details),1)
        self.assertNotIn('open',p.details[0])
        self.assertIn('Historique des anomalies de DIS',quality_card(row))

    def test_unavailable_business_methods_remain_reachable_in_closed_details(self):
        row={'sector_indicators':{'family':'Test','published_kpis':{'x':{'label':'Production','value':None,'reason':'Unité à confirmer'}}}}
        page=sector_card(row);p=Tags();p.feed(page)
        self.assertIn('Unité à confirmer',page)
        self.assertIn('data-sector-missing',p.details[0]);self.assertNotIn('open',p.details[0])
        self.assertIn('id="metier"',page)
