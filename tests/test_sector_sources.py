"""Sector publication discovery must not contaminate listed-issuer financials."""
import copy
import json
from pathlib import Path
import unittest

from nour.sector_sources import (collect, extract_links, monitor_html,
                                 read_config, validate_config, validate_state)

ROOT = Path(__file__).resolve().parents[1]


class SectorSourceTests(unittest.TestCase):
    def setUp(self):
        self.config = read_config(ROOT / "data/sector_source_watch.json")

    def test_seven_official_watches_have_no_financial_score_authority(self):
        self.assertEqual(len(self.config["sources"]), 7)
        self.assertFalse(self.config["usable_for_score"])
        self.assertFalse(self.config["usable_for_issuer_ratios"])
        self.assertEqual({s["id"] for s in self.config["sources"]},
                         {"BAM", "ACAPS", "HCP", "OFFICE_CHANGES", "ANP", "ONDA", "TANGER_MED"})

    def test_only_allowed_origin_documents_and_relevant_links_are_indexed(self):
        source = self.config["sources"][0]
        html = b"""<a href="/file.pdf">Statistiques monetaires</a>
        <a href="https://evil.example/private.pdf">Wrong origin</a>
        <a href="/foo">Other unrelated</a>
        <a href="/credits">Credit bancaire</a>
        <a href="http://www.bkam.ma/insecure.pdf">Insecure</a>"""
        links = extract_links(html, source["url"], source["origins"], source["keywords"])
        self.assertEqual(len(links), 2)
        self.assertTrue(all(link["url"].startswith("https://www.bkam.ma/") for link in links))
        self.assertEqual({link["type"] for link in links},
                         {"document_candidate", "related_page"})

    def test_failure_preserves_last_good_without_fake_freshness(self):
        calls = []
        def fetcher(url, origins, **kwargs):
            calls.append(url)
            if "acaps" in url:
                raise OSError("site unavailable")
            return (b'<a href="/public.pdf">Statistiques du secteur</a>',
                    url, "text/html")
        first = collect(self.config, fetcher=fetcher, now="2026-10-16T12:00:00+00:00")
        self.assertEqual(first["status"], "partial")
        self.assertEqual(first["sources"]["ACAPS"]["status"], "error")
        self.assertEqual(len(calls), 7)
        self.assertFalse(first["usable_for_score"])
        self.assertFalse(first["usable_for_issuer_ratios"])
        bam = first["sources"]["BAM"]
        self.assertEqual(bam["links"][0]["first_seen_at"], "2026-10-16T12:00:00+00:00")

        def all_fail(url, origins, **kwargs):
            raise OSError("timeout")
        second = collect(self.config, first, fetcher=all_fail,
                         now="2026-10-17T12:00:00+00:00")
        self.assertEqual(second["status"], "error")
        self.assertEqual(second["sources"]["BAM"]["last_success_at"], first["checked_at"])
        self.assertEqual(second["sources"]["BAM"]["links"], bam["links"])
        self.assertEqual(second["sources"]["BAM"]["checked_at"], second["checked_at"])
        self.assertEqual(first["sources"]["BAM"]["status"], "success")

    def test_config_rejects_non_official_redirect_origins_and_duplicates(self):
        modified = copy.deepcopy(self.config)
        modified["sources"][0]["url"] = "http://127.0.0.1/internal"
        with self.assertRaises(ValueError):
            validate_config(modified)
        modified = copy.deepcopy(self.config)
        modified["sources"].append(copy.deepcopy(modified["sources"][0]))
        with self.assertRaises(ValueError):
            validate_config(modified)
        with self.assertRaises(ValueError):
            validate_state({"schema_version": 1, "sources": {}})

    def test_display_escapes_external_titles_and_shows_staleness(self):
        sample = collect(self.config, fetcher=lambda url, origins, **kw: (
            b'<a href="/report.pdf"><script>alert(1)</script> rapport</a>', url, "text/html"),
            now="2026-10-16T10:00:00+00:00")
        rendered = monitor_html(sample)
        self.assertNotIn("<script>", rendered)
        self.assertIn("Dernier succès", rendered)
        self.assertIn("Première collecte non exécutée", monitor_html(None))


if __name__ == "__main__":
    unittest.main()
