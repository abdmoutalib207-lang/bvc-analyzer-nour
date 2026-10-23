"""Source-preserving follow-up: native ratios, expense bridge and 80-title parity."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import unittest
from nour.engine import build_report
from nour.sector_calculators import calculate_sector
from nour.sector_validation import audit_sector_calculations
from nour.sector_view import sector_card
from tools.import_finance_followup_oct23 import reconcile

ROOT = Path(__file__).resolve().parents[1]
DAY = '2026-10-23'


class FinancialFollowupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads((ROOT/'data/facts_reference.json').read_text())
        cls.review = json.loads((ROOT/'knowledge/financial_reviews/2026-10-23-followup.json').read_text())

    def sector(self, symbol, facts=None):
        return calculate_sector(symbol, {}, facts or self.payload['records'][symbol], DAY)

    def test_replay_is_idempotent_and_preserves_every_historical_input(self):
        self.assertEqual(reconcile(self.payload, self.review), self.payload)
        before = deepcopy(self.payload)
        for s in self.review['records']:
            before['records'][s].pop('sector_faits')
            before['records'][s].pop('sector_review_followup')
        after = reconcile(before, self.review)
        for s in before['records']:
            self.assertEqual(before['records'][s]['faits'], after['records'][s]['faits'], s)
            self.assertEqual(before['records'][s].get('latest_report'), after['records'][s].get('latest_report'), s)
        for mutate in ('url', 'exercice'):
            bad = deepcopy(before); bad['records']['MUT'][mutate] = 'changed'
            with self.assertRaises(ValueError): reconcile(bad, self.review)
        bad = deepcopy(after); bad['records']['MUT']['sector_faits']['chiffre_affaires']['valeur'] += 1
        with self.assertRaises(ValueError): reconcile(bad, self.review)

    def test_enk_ratios_use_native_currency_without_releasing_mad_amounts(self):
        m = self.sector('ENK')['metrics']
        expected = dict(operating_margin_pct=100*Fraction(78487051,717159964),
            group_margin_pct=100*Fraction(59657964,717159964),
            capex_revenue_pct=100*Fraction(12182432,717159964),
            operating_cash_margin_pct=100*Fraction(37007597,717159964),
            asset_turnover=2*Fraction(717159964,512318302+443518793),
            inventory_turnover=2*Fraction(580013991,195008393+154485171),
            native_group_roe_closing_pct=100*Fraction(59657964,279606768),
            native_group_roe_average_pct=200*Fraction(59657964,247378976+279606768))
        self.assertEqual({k for k,v in m.items() if v['value'] is not None}, set(expected))
        for k,v in expected.items():
            self.assertAlmostEqual(m[k]['value'], float(v), delta=.00005001)
            self.assertEqual(m[k]['currency'], 'TND')
            self.assertFalse(m[k]['currency_conversion_applied'])
            self.assertFalse(m[k]['used_for_score'])
        self.assertIsNone(m['free_cash_after_capex_mmad']['value'])
        self.assertIn('sans conversion de change', sector_card({'sector_indicators': self.sector('ENK')}))

    def test_foreign_units_currencies_periods_and_signed_cost_are_not_inferred(self):
        for field,value in [('devise','MAD'),('devise',None),('unite','MMAD'),('unite_au_rapport','MAD'),('period_end','2026-06-30'),('valeur_au_rapport',580013991),('normalization','unknown')]:
            f = deepcopy(self.payload['records']['ENK'])
            f['sector_faits']['cout_des_ventes'][field] = value
            m = self.sector('ENK',f)['metrics']
            self.assertIsNone(m['inventory_turnover']['value'], (field,value))
            self.assertEqual(m['group_margin_pct']['value'],8.3186)
        f=deepcopy(self.payload['records']['ENK']);f['sector_faits']['chiffre_affaires'].pop('devise')
        self.assertIsNone(self.sector('ENK',f)['metrics']['group_margin_pct']['value'])

    def test_native_roe_rejects_only_the_incompatible_denominator(self):
        for field,value in [('valeur',0),('valeur',-1),('period_end','2025-12-31'),('base','social SCE tunisien')]:
            f=deepcopy(self.payload['records']['ENK'])
            f['sector_faits']['capitaux_propres_groupe_ouverture'][field]=value
            m=self.sector('ENK',f)['metrics']
            self.assertIsNone(m['native_group_roe_average_pct']['value'],field)
            self.assertEqual(m['native_group_roe_closing_pct']['value'],21.3364)
            self.assertEqual(m['group_margin_pct']['value'],8.3186)

    def test_cfg_cost_income_includes_depreciation_and_excludes_credit_risk(self):
        f = deepcopy(self.payload['records']['CFGB'])
        self.assertEqual(self.sector('CFGB',f)['metrics']['cost_income_pct']['value'],49.2277)
        for mutation in ('amount', 'sign', 'source', 'missing'):
            bad=deepcopy(f);charges=bad['sector_faits']['charges_generales_exploitation']
            if mutation=='amount':charges['valeur']=513.422
            elif mutation=='sign':charges['components'][1]['valeur_au_rapport']=100560
            elif mutation=='source':charges['components'][1]['document_hash']='sha256:'+'0'*64
            else:charges['components'].pop()
            self.assertIsNone(self.sector('CFGB',bad)['metrics']['cost_income_pct']['value'],mutation)

    def test_independent_auditor_rejects_foreign_ratio_mislabelling(self):
        block = self.sector('ENK')
        report = {'results':[{'symbol':'ENK','sector_indicators':block}]}
        self.assertEqual(audit_sector_calculations(report)['arithmetic_checks'],8)
        self.assertFalse(audit_sector_calculations(report)['failures'])
        for field,value in [('devise','MAD'),('unite','MMAD')]:
            bad=deepcopy(report)
            bad['results'][0]['sector_indicators']['metrics']['group_margin_pct']['inputs']['chiffre_affaires'][field]=value
            self.assertTrue(audit_sector_calculations(bad)['failures'])

    def test_all_80_technical_fundamental_and_score_results_remain_identical(self):
        fixture=json.loads((ROOT/'data/market_snapshot.json').read_text())
        old=deepcopy(self.payload['records'])
        for s in self.review['records']:
            old[s].pop('sector_faits');old[s].pop('sector_review_followup')
        baseline=build_report(fixture,DAY,facts=old)
        changed=build_report(fixture,DAY,facts=self.payload['records'])
        self.assertEqual(len(changed['results']),80)
        for before,after in zip(baseline['results'],changed['results']):
            symbol=before['symbol'];b=deepcopy(before);a=deepcopy(after)
            b.pop('sector_indicators');a.pop('sector_indicators')
            self.assertEqual(b,a,symbol)
            for key,m in before['sector_indicators']['metrics'].items():
                if m['value'] is not None:
                    self.assertEqual(m['value'],after['sector_indicators']['metrics'][key]['value'],(symbol,key))
        rows={r['symbol']:r for r in changed['results']}
        for s in ('CFGB','CMGP','SGTM','ENK'):
            self.assertIsNone(rows[s]['fundamental']['pe'],s)
        for s in ('ADI','MUT'):
            self.assertIsNone(rows[s]['fundamental']['net_debt_ebitda'],s)
