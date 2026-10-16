import json
from pathlib import Path
import tempfile
import unittest
from urllib.request import Request
from unittest.mock import patch, MagicMock

from nour.official_sources import (_Redirect, AMMC_INDEX, collect, document_links,
                                   safe_url, validate_registry, validate_state, fetch)


class OfficialSourcesTests(unittest.TestCase):
    def setUp(self):
        self.origins = ['https://www.ammc.ma', 'https://issuer.ma']
        self.page = 'https://issuer.ma/investors'
        self.registry = {'schema_version': 1, 'issuers': {
            'ADI': {'record_id': 'ADI', 'name': 'Alliances',
                    'allowed_origins': self.origins, 'pages': [self.page]}}}

    def fetcher(self, url, origins, **kwargs):
        if url == AMMC_INDEX:
            return b'<a href="/sites/alliances.pdf">Alliances resultats</a>', url, 'text/html'
        if url == self.page:
            return b'<a href="/report.pdf#page=3">Report</a>', url, 'text/html'
        return b'%PDF-1.7 identical content', url, 'application/pdf'

    def test_registry_matches_complete_universe(self):
        root = Path(__file__).resolve().parents[1]
        registry = json.loads((root / 'data/official_sources.json').read_text())
        snapshot = json.loads((root / 'data/market_snapshot.json').read_text())
        validate_registry(registry)
        self.assertEqual(set(registry['issuers']), set(snapshot['symbols']))
        self.assertEqual(len(registry['issuers']), 80)

    def test_rejects_external_credentials_ports_and_lookalike(self):
        for url in ['http://issuer.ma/a.pdf', 'https://issuer.ma.evil/a.pdf',
                    'https://issuer.ma@evil/a.pdf', 'https://issuer.ma:8443/a.pdf',
                    'file:///etc/passwd', 'https://issuer.ma\\@evil/a.pdf']:
            self.assertIsNone(safe_url(url, self.origins))

    def test_redirect_checked_before_request(self):
        with self.assertRaises(ValueError):
            _Redirect(self.origins).redirect_request(Request(self.page), None, 302,
                'Found', {}, 'https://evil.test/a.pdf')

    def test_relative_links_queries_and_dedup(self):
        body = b'<a href="/r.pdf?x=1#p">One</a><a href="/r.pdf?x=1">Two</a><a href="https://evil.test/r.pdf">No</a>'
        docs = document_links(body, self.page, self.origins)
        self.assertEqual([r['url'] for r in docs], ['https://issuer.ma/r.pdf?x=1'])

    def test_download_dedup_is_content_based_and_not_verified(self):
        with tempfile.TemporaryDirectory() as folder:
            result = collect(self.registry, fetcher=self.fetcher,
                fetch_documents=True, cache_dir=folder, now='2026-10-16T00:00:00Z')
            self.assertEqual(result['status'], 'ok')
            self.assertEqual(len(result['documents']), 2)
            self.assertEqual(len(list(Path(folder).glob('*.pdf'))), 1)
            for doc in result['documents']:
                self.assertEqual(doc['status'], 'downloaded_not_read')
                self.assertFalse(doc['usable_for_score'])
                self.assertEqual(len(doc['identical_content_urls']), 2)

    def test_failure_preserves_last_good_and_distinguishes_no_new(self):
        result = collect(self.registry, fetcher=self.fetcher, now='first')
        unchanged = collect(self.registry, result, fetcher=self.fetcher, now='second')
        self.assertTrue(all(s['status'] == 'no_new' for s in unchanged['sources'].values()))
        def broken(*args, **kwargs):
            raise TimeoutError('timed out')
        failed = collect(self.registry, unchanged, fetcher=broken, now='third')
        self.assertEqual(failed['documents'], unchanged['documents'])
        self.assertEqual(failed['status'], 'error')
        self.assertTrue(all(s['last_success_at'] == 'second' for s in failed['sources'].values()))
        self.assertEqual(result['sources'][self.page]['last_success_at'], 'first')

    def test_fetch_rejects_oversized_response(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.geturl.return_value = self.page
        response.headers = {'Content-Type': 'text/html'}
        response.read.return_value = b'x' * 11
        opener = MagicMock()
        opener.open.return_value = response
        with patch('nour.official_sources.build_opener', return_value=opener):
            with self.assertRaisesRegex(ValueError, 'size limit'):
                fetch(self.page, self.origins, max_bytes=10)
        response.read.assert_called_once_with(11)

    def test_single_word_issuer_names_match_official_titles(self):
        registry = {'schema_version': 1, 'issuers': {'VCNE': {
            'record_id': 'VCNE', 'name': 'Vicenne', 'aliases': ['Vicenne'],
            'allowed_origins': ['https://www.ammc.ma'], 'pages': []}}}
        def official(url, origins, **kwargs):
            return b'<a href="/report.pdf">Vicenne - resultats S1 2026</a>', url, 'text/html'
        result = collect(registry, fetcher=official)
        self.assertEqual(result['documents'][0]['tickers'], ['VCNE'])

    def test_corrected_pdf_same_url_refreshes_hash_and_keeps_history(self):
        first = collect(self.registry, fetcher=self.fetcher, fetch_documents=True, now='first')
        def corrected(url, origins, **kwargs):
            if '.pdf' in url:
                return b'%PDF-1.7 corrected', url, 'application/pdf'
            return self.fetcher(url, origins, **kwargs)
        second = collect(self.registry, first, fetcher=corrected, fetch_documents=True, now='second')
        self.assertNotEqual(first['documents'][0]['sha256'], second['documents'][0]['sha256'])
        self.assertEqual(second['documents'][0]['content_history'][0]['sha256'],
                         first['documents'][0]['sha256'])
        def failure(url, origins, **kwargs):
            if '.pdf' in url:
                raise TimeoutError('timeout')
            return self.fetcher(url, origins, **kwargs)
        third = collect(self.registry, second, fetcher=failure, fetch_documents=True, now='third')
        self.assertEqual(second['documents'][0]['sha256'], third['documents'][0]['sha256'])
        self.assertEqual(third['documents'][0]['fetch_status'], 'error')
        self.assertEqual(third['documents'][0]['fetched_at'], 'second')

    def test_candidate_associations_explain_evidence_and_never_certify_ownership(self):
        result = collect(self.registry, fetcher=self.fetcher)
        methods = {e['method'] for d in result['documents'] for e in d['match_evidence']}
        self.assertEqual(methods, {'issuer_page', 'official_index_name'})
        self.assertTrue(all(not d['pdf_issuer_ownership_validated'] for d in result['documents']))
        self.assertTrue(all(d['association_status'] == 'candidate_only_unverified'
                            for d in result['documents']))
        def ticker_only(url, origins, **kwargs):
            if url == AMMC_INDEX:
                return b'<a href="/ADI.pdf">Generic resultats</a>', url, 'text/html'
            return self.fetcher(url, origins, **kwargs)
        other = collect(self.registry, fetcher=ticker_only)
        self.assertFalse(any('/ADI.pdf' in d['url'] for d in other['documents']))

    def test_malformed_previous_shape_fails_before_network(self):
        for state in [[], {}, {'schema_version': 1, 'documents': {}, 'sources': {}},
                      {'schema_version': 1, 'documents': [], 'sources': {'url': []}},
                      {'schema_version': 1, 'documents': [{'id': 'x'}], 'sources': {}}]:
            with self.assertRaises(ValueError):
                collect(self.registry, state, fetcher=MagicMock(side_effect=AssertionError('network')))

    def test_cli_malformed_json_and_state_preserve_original_bytes(self):
        from tools.update_official_sources import main
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = root / 'data'
            data.mkdir()
            (data / 'official_sources.json').write_text(json.dumps(self.registry))
            target = data / 'official_document_candidates.json'
            for invalid in [b'{broken JSON', b'{"schema_version":1,"documents":{},"sources":{}}']:
                target.write_bytes(invalid)
                with patch('tools.update_official_sources.collect') as network:
                    self.assertEqual(main([], root), 1)
                    network.assert_not_called()
                self.assertEqual(target.read_bytes(), invalid)
                health = json.loads((data / 'official_sources_health.json').read_text())
                self.assertEqual(health['status'], 'error')
                self.assertTrue(health['candidate_file_preserved'])

    def test_bad_pdf_not_certified_and_budget_bounded(self):
        calls = []
        def wrong_pdf(url, origins, **kwargs):
            calls.append(url)
            if '.pdf' in url:
                return b'HTML error page', url, 'text/html'
            return self.fetcher(url, origins, **kwargs)
        result = collect(self.registry, fetcher=wrong_pdf, fetch_documents=True, max_documents=1)
        self.assertEqual(sum('.pdf' in url for url in calls), 1)
        self.assertFalse(any(d.get('sha256') for d in result['documents']))
        self.assertEqual(sum('fetch_error' in d for d in result['documents']), 1)


if __name__ == '__main__':
    unittest.main()
