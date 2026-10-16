"""Financial gates exercise adversarial inputs, not score expectations."""
import copy
import json
import unittest
from pathlib import Path

from nour.financial_audit import audit_financials, apply_financial_audit, audit_dataset
from nour.fundamentals import calculate


def fact(value, unit='MMAD', period='2025-12-31', basis='consolidé IFRS'):
    return dict(valeur=value, unite=unit, period_end=period, base=basis, page=2,
                url='https://issuer.example/results.pdf', document_hash='sha256:' + 'a' * 64,
                validation_status='selected_pages_visually_checked')


def facts():
    return dict(exercice=2025, exercice_clos='2025-12-31', devise='MAD',
                url='https://issuer.example/results.pdf', accounting_basis='consolidé IFRS',
                faits=dict(resultat_net_part_groupe=fact(20),
                           capitaux_propres_part_groupe=fact(200),
                           nombre_actions=fact(1000000, 'actions'),
                           chiffre_affaires=fact(300),
                           chiffre_affaires_2024=fact(250, period='2024-12-31'),
                           dettes_financieres=fact(120), tresorerie_actif=fact(20),
                           endettement_net=fact(100), excedent_brut_exploitation=fact(40)))


class FinancialAuditTests(unittest.TestCase):
    def audit(self, f):
        return audit_financials({'symbol': 'TEST', 'price': 100}, f, '2026-10-16')

    def codes(self, audit):
        return {c['code'] for c in audit['checks']}

    def test_central_calculation_boundary_cannot_bypass_explicit_contracts(self):
        from nour.analytics import fundamentals
        f = facts()
        f['faits']['nombre_actions']['unite'] = 'MMAD'
        out = calculate({'price': 100}, f, asof='2026-10-16')
        self.assertIsNone(out['eps_mad'])
        self.assertIsNone(out['pe'])
        self.assertEqual(out['roe_pct'], 10)
        self.assertIn('eps_mad', out['financial_audit']['blocked_metrics'])
        # The public analytics entrypoint delegates to the same calculation.
        delegated = fundamentals({'price': 100}, f)
        self.assertIsNone(delegated['eps_mad'])
        self.assertIn('financial_audit', delegated)

    def test_verified_arithmetic_and_no_mutation(self):
        f = facts()
        before = copy.deepcopy(f)
        a = self.audit(f)
        self.assertEqual(a['blocked_metrics'], [])
        self.assertEqual(a['debt_comparison']['status'], 'within_tolerance')
        raw = calculate({'price': 100}, f)
        raw_before = copy.deepcopy(raw)
        gated = apply_financial_audit(raw, a)
        self.assertEqual(gated['roe_pct'], 10)
        self.assertEqual(gated['net_debt_ebitda'], 2.5)
        self.assertEqual(raw, raw_before)
        self.assertEqual(f, before)

    def test_wrong_unit_or_fractional_shares_withhold_only_affected_outputs(self):
        for value, unit in [(1000000, 'MMAD'), (1.5, 'actions'), (0, 'actions'),
                            (-4, 'actions'), (True, 'actions'), (float('nan'), 'actions')]:
            with self.subTest(value=value, unit=unit):
                f = facts()
                f['faits']['nombre_actions'].update(valeur=value, unite=unit)
                a = self.audit(f)
                for metric in ('eps_mad', 'pe', 'pb', 'book_value_per_share_mad'):
                    self.assertIn(metric, a['blocked_metrics'])
                self.assertNotIn('roe_pct', a['blocked_metrics'])

    def test_displayed_earnings_and_pnb_share_ratio_unit_and_period_guards(self):
        # An incorrect RNPG unit previously left a false amount visible even
        # though BPA/PER/ROE were withheld by the financial audit.
        f = facts()
        f['faits']['resultat_net_part_groupe']['unite'] = 'KMAD'
        result = calculate({'price': 100}, f, asof='2026-10-16')
        self.assertIsNone(result['earnings_mmad'])
        self.assertIsNone(result['eps_mad'])
        self.assertIsNone(result['pe'])
        self.assertIsNone(result['roe_pct'])
        self.assertEqual(result['revenue_growth_pct'], 20)
        self.assertIn('earnings_mmad', result['financial_audit']['blocked_metrics'])

        f = facts()
        f['faits']['produit_net_bancaire'] = fact(150, period='2024-12-31')
        f['faits']['produit_net_bancaire_2024'] = fact(120, period='2024-12-31')
        result = calculate({'price': 100}, f, asof='2026-10-16')
        self.assertIsNone(result['pnb_mmad'])
        self.assertIsNone(result['pnb_growth_pct'])
        self.assertEqual(result['earnings_mmad'], 20)
        self.assertIn('pnb_mmad', result['financial_audit']['blocked_metrics'])

    def test_displayed_earnings_can_be_negative_without_fabricated_positive_per(self):
        f = facts()
        f['faits']['resultat_net_part_groupe']['valeur'] = -20
        result = calculate({'price': 100}, f, asof='2026-10-16')
        self.assertEqual(result['earnings_mmad'], -20)
        self.assertIsNone(result['pe'])
        self.assertEqual(result['eps_mad'], -20)

    def test_explicit_cross_period_or_social_group_mix_is_blocked(self):
        f = facts()
        f['faits']['capitaux_propres_part_groupe']['period_end'] = '2026-06-30'
        self.assertIn('roe_pct', self.audit(f)['blocked_metrics'])
        f = facts()
        f['faits']['capitaux_propres_sociaux'] = f['faits'].pop('capitaux_propres_part_groupe')
        self.assertIn('earnings_equity_scope_mismatch', self.codes(self.audit(f)))
        self.assertIn('roe_pct', self.audit(f)['blocked_metrics'])
        self.assertNotIn('eps_mad', self.audit(f)['blocked_metrics'])

    def test_debt_difference_only_compared_on_same_explicit_basis(self):
        f = facts()
        f['faits']['endettement_net']['valeur'] = 80
        a = self.audit(f)
        self.assertEqual(a['debt_comparison']['difference_mmad'], 20)
        self.assertIn('net_debt_strict_mmad', a['blocked_metrics'])
        f['faits']['endettement_net']['base'] = 'social normes marocaines'
        a = self.audit(f)
        self.assertEqual(a['debt_comparison']['status'], 'not_comparable')
        self.assertNotIn('debt_arithmetic_mismatch', self.codes(a))
        # Different published definition cannot invalidate the strict amount.
        self.assertNotIn('net_debt_strict_mmad', a['blocked_metrics'])
        f['faits']['endettement_net'].pop('base')
        self.assertEqual(self.audit(f)['debt_comparison']['status'], 'not_comparable')

    def test_foreign_currency_huge_integer_and_negative_inputs_are_not_ratios(self):
        f = facts()
        f['devise'] = 'USD'
        self.assertIn('eps_mad', self.audit(f)['blocked_metrics'])
        f = facts()
        f['faits']['dettes_financieres']['valeur'] = 10 ** 1000
        self.assertIn('net_debt_ebitda', self.audit(f)['blocked_metrics'])
        f['faits']['dettes_financieres']['valeur'] = -1
        self.assertIn('net_debt_strict_mmad', self.audit(f)['blocked_metrics'])
        f['faits']['dividende_par_action'] = fact(-2, 'MAD')
        self.assertIn('dividend_yield_pct', self.audit(f)['blocked_metrics'])

    def test_core_debt_inputs_must_be_compatible_and_ebe_positive(self):
        f = facts()
        f['faits']['tresorerie_actif']['base'] = 'social'
        self.assertIn('net_debt_strict_mmad', self.audit(f)['blocked_metrics'])
        f = facts()
        f['faits']['excedent_brut_exploitation']['valeur'] = -10
        a = self.audit(f)
        self.assertIn('net_debt_ebitda', a['blocked_metrics'])
        self.assertNotIn('net_debt_strict_mmad', a['blocked_metrics'])

    def test_loss_is_observed_not_missing_and_negative_equity_not_positive_roe(self):
        f = facts()
        f['faits']['resultat_net_part_groupe']['valeur'] = -20
        a = self.audit(f)
        self.assertIn('pe', a['blocked_metrics'])
        self.assertNotIn('eps_mad', a['blocked_metrics'])
        self.assertNotIn('roe_pct', a['blocked_metrics'])
        f['faits']['capitaux_propres_part_groupe']['valeur'] = -200
        self.assertIn('roe_pct', self.audit(f)['blocked_metrics'])
        self.assertNotIn('book_value_per_share_mad', self.audit(f)['blocked_metrics'])

    def test_annual_semester_freshness_does_not_annualize_or_overwrite(self):
        f = facts()
        f['exercice'] = 2024
        f['exercice_clos'] = '2024-12-31'
        f['latest_report'] = dict(period_end='2026-06-30', reported_net_millions=500)
        a = self.audit(f)
        self.assertTrue(a['freshness']['newer_report_available'])
        self.assertEqual(a['freshness']['annual_years_behind_latest'], 2)
        self.assertIn('annual_reference_older_than_latest_year', self.codes(a))
        self.assertEqual(f['faits']['resultat_net_part_groupe']['valeur'], 20)
        f['exercice_clos'] = '2026-12-31'
        self.assertIn('annual_period_future', self.codes(self.audit(f)))

    def test_unverified_sources_are_pending_not_certified_and_total_is_no_substitute(self):
        f = facts()
        for item in f['faits'].values():
            item.pop('document_hash')
        self.assertEqual(self.audit(f)['status'], 'review_required')
        f['faits']['resultat_net_consolide'] = f['faits'].pop('resultat_net_part_groupe')
        a = self.audit(f)
        self.assertIn('group_earnings_missing_total_not_substituted', self.codes(a))
        self.assertIn('eps_mad', a['blocked_metrics'])

    def test_dh_is_mad_and_prose_labels_are_not_scope_proof(self):
        f = facts()
        f['faits']['dividende_par_action'] = fact(5, 'DH')
        f['faits']['dettes_financieres']['base'] += ' — états complets p.104'
        self.assertNotIn('dividend_yield_pct', self.audit(f)['blocked_metrics'])
        self.assertNotIn('net_debt_strict_mmad', self.audit(f)['blocked_metrics'])
        self.assertEqual(self.audit(f)['debt_comparison']['status'], 'not_comparable')

    def test_real_source_inventory_serializable_and_asof_required(self):
        root = Path(__file__).resolve().parents[1]
        source = json.loads((root / 'data/facts_reference.json').read_text())['records']
        result = audit_dataset(source, {}, '2026-10-16')
        self.assertEqual(result['summary']['issuers'], len(source))
        self.assertIn('ADI', result['issuers'])
        self.assertIn('VCNE', result['issuers'])
        json.dumps(result, allow_nan=False)
        with self.assertRaises(ValueError):
            audit_dataset(source, {}, 'not-a-date')

    def test_scope_bridge_preserves_previously_reconciled_debt(self):
        f = facts()
        f['faits']['endettement_net']['valeur'] = 90
        raw = calculate({'price': 100}, f)
        raw['debt_reconciliation']['status'] = 'scope_reconciled'
        raw['net_debt_strict_mmad'] = 100
        raw['net_debt_ebitda'] = 2.5
        a = audit_financials({'price': 100}, f, '2026-10-16', raw)
        self.assertNotIn('net_debt_strict_mmad', a['blocked_metrics'])
        self.assertEqual(a['debt_comparison']['status'], 'scope_reconciled')


if __name__ == '__main__':
    unittest.main()
