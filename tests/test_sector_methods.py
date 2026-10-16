"""Sector rules are descriptive, isolated from numerical scoring."""
import unittest
import json
from pathlib import Path

from nour.sector_methods import FAMILIES, guidance


class SectorMethodsTests(unittest.TestCase):
    def test_curated_tickers_are_real_nour_symbols_not_source_aliases(self):
        symbols = set(json.loads((Path(__file__).resolve().parents[1] / 'data/source_codes.json').read_text()))
        curated = set()
        for family, details in FAMILIES.items():
            for ticker in details['symbols']:
                self.assertIn(ticker, symbols, (family, ticker))
                curated.add(ticker)
        self.assertEqual(len(curated), 78)
        self.assertEqual(symbols - curated, {"DIS", "HAL"})
        self.assertEqual(guidance("DIS")["coverage"], "broad_only")
        self.assertEqual(guidance("HAL")["coverage"], "broad_only")

    def test_curated_families_do_not_overlap(self):
        seen = set()
        for family, data in FAMILIES.items():
            self.assertTrue(family)
            self.assertTrue(data["metrics"])
            self.assertTrue(data["exclude"])
            for symbol in data["symbols"]:
                self.assertNotIn(symbol, seen)
                seen.add(symbol)

    def test_sectors_require_distinct_evidence(self):
        bank = guidance("ATW")
        hotel = guidance("RIS")
        btp = guidance("SGTM")
        health = guidance("SOT")
        self.assertIn("PNB", bank["metrics_to_verify"])
        self.assertIn("RevPAR", hotel["metrics_to_verify"])
        self.assertIn("carnet de commandes", btp["metrics_to_verify"])
        self.assertIn("mix produits", health["metrics_to_verify"])
        self.assertNotEqual(bank["family"], hotel["family"])
        self.assertIn("PNB bancaire", hotel["invalid_shortcuts"])
        self.assertIn("ARPU", guidance("IAM")["metrics_to_verify"])
        self.assertIn("volumes ciment", guidance("LHM")["metrics_to_verify"])
        self.assertIn("EVP", guidance("MSA")["metrics_to_verify"])
        self.assertIn("revenus récurrents si publiés", guidance("T2S")["metrics_to_verify"])

    def test_health_businesses_and_hospital_kpis_are_not_conflated(self):
        hospital = guidance("AKD")
        pharma = guidance("SOT")
        distributor = guidance("VCNE")
        self.assertEqual(len({hospital["family"], pharma["family"], distributor["family"]}), 3)
        self.assertIn("capacité lits", hospital["metrics_to_verify"])
        self.assertIn("mix produits", pharma["metrics_to_verify"])
        self.assertIn("marge de distribution", distributor["metrics_to_verify"])
        self.assertIn("rotation des stocks comme indicateur principal", hospital["invalid_shortcuts"])

    def test_agribusiness_and_farming_inputs_are_separate(self):
        self.assertNotEqual(guidance("MUT")["family"], guidance("CMGP")["family"])
        self.assertIn("coûts des intrants", guidance("CSR")["metrics_to_verify"])

    def test_unknown_symbol_abstains(self):
        result = guidance("UNKNOWN", {"sector": "Autres"})
        self.assertEqual(result["coverage"], "broad_only")
        self.assertEqual(result["metrics_to_verify"], [])
        self.assertIn("non validée", result["note"])

    def test_guidance_returns_independent_mutable_copy(self):
        first = guidance("ADI")
        first["metrics_to_verify"].append("inventé")
        self.assertNotIn("inventé", guidance("ADI")["metrics_to_verify"])

    def test_no_measured_values_or_investment_signals(self):
        for family in FAMILIES.values():
            self.assertNotIn("score", family)
            self.assertNotIn("buy", family)
            self.assertNotIn("value", family)


if __name__ == "__main__":
    unittest.main()
