"""Extraction failures must never invent numbers, erase history or affect scores."""
from copy import deepcopy
import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from nour.sector_ingestion import extract,collect,DiscoveryLinks,safe_url,discovered_url
from nour.business_disclosures import disclosure_view
ROOT=Path(__file__).resolve().parents[1]

class SectorIngestionTests(unittest.TestCase):
    def setUp(self):self.config=json.loads((ROOT/'knowledge/sector_extraction_profiles.json').read_text())
    def tgcc(self,text=None,digest='a'*64):
        p=self.config['profiles'][0]
        pages=['TGCC Résultats semestriels AU 30 JUIN 2026','S1 2026    S1 2025\n'+(text or 'Carnet de commandes (M MAD)   28 360       19 100      +9 260')]
        return extract(p,pages,p['seeds'][0],digest,'2026-10-24T15:00:00+00:00')
    def test_precise_table_columns_and_periods_not_rounded_narrative(self):
        rows,doc,c=self.tgcc();self.assertFalse(c)
        self.assertEqual([(r['value'],r['period_end']) for r in rows],[(28360,'2026-06-30'),(19100,'2025-06-30')])
        self.assertEqual(doc['review_status'],'automatic_text_extraction')
        self.assertEqual(rows[0]['page'],2)
    def test_ambiguous_layout_and_wrong_issuer_or_future_period(self):
        rows,doc,c=self.tgcc(('Carnet de commandes (M MAD)  28 360    19 100\n')*2)
        self.assertFalse(rows);self.assertEqual(c[0]['matches'],2)
        p=self.config['profiles'][0]
        for head in ['Autre société AU 30 JUIN 2026','TGCC AU 30 JUIN 2027']:
            with self.assertRaises(ValueError):extract(p,[head],'https://www.ammc.ma/a.pdf','a'*64,'2026-10-24')
    def test_container_component_mismatch_keeps_other_fields(self):
        p=self.config['profiles'][1]
        page='''Marsa Maroc AU 30 JUIN 2026
34,5 MILLIONS DE TONNES
TRAFIC CONSOLIDÉ
1.520.260 EVP(*)
TRAFIC DE TRANSBORDEMENT : 822.666 EVP
TRAFIC IMPORT-EXPORT : 697.595 EVP
'''
        rows,_,c=extract(p,[page],p['seeds'][0],'b'*64,'2026-10-24')
        self.assertEqual([r['id'] for r in rows],['traffic-total-2026-06-30'])
        self.assertTrue(any(x['reason']=='component_sum_mismatch' for x in c))
    def test_outage_retains_previous_records_without_rewriting_dates(self):
        state=json.loads((ROOT/'data/sector_disclosures.json').read_text());before=deepcopy(state)
        def fail(*a,**kw):raise OSError('offline')
        out=collect(self.config,state,{},Path('/tmp/unused'),now='2026-10-25T15:00:00+00:00',fetch=fail,page_fetch=fail)
        self.assertEqual(state,before)
        for symbol in state['catalogues']:
            for key in ('records','documents','available_from','reviewed_on'):
                self.assertEqual(out['catalogues'][symbol][key],state['catalogues'][symbol][key])
        self.assertTrue(out['incidents'])
        self.assertTrue(all(h['retained_previous'] for h in out['health'].values()))
    def test_review_is_bound_to_the_pdf_hash_and_approximation_is_retained(self):
        c=json.loads((ROOT/'data/sector_disclosures.json').read_text())['catalogues']['SMI']
        view=disclosure_view(c,'2026-10-24');aisc=next(r for r in view['records'] if r['category']=='unit_cost')
        self.assertEqual((aisc['value'],aisc['unit'],aisc['approximate']),(22,'USD/oz',True))
        self.assertEqual(aisc['status'],'primary_page_checked')
        c=deepcopy(c)
        for d in c['documents'].values():d['review_status']='automatic_text_extraction'
        self.assertTrue(all(r['status']=='automatic_text_extracted' for r in disclosure_view(c,'2026-10-24')['records']))

    def test_new_publications_are_discovered_from_official_titles_including_native_downloads(self):
        p=DiscoveryLinks();p.feed('<li>Résultats Semestriels au 30 Juin 2027<a href="/?jet_download='+'a'*40+'">Télécharger</a></li><li>Autre document<a href="x.pdf">Télécharger</a></li>')
        self.assertIn('2027',p.links[0][1]);self.assertNotIn('2027',p.links[1][1])
        self.assertTrue(safe_url('https://tgcc.ma/?jet_download='+'a'*40,['tgcc.ma']))
        self.assertFalse(safe_url('https://tgcc.ma/?delete=1',['tgcc.ma']))

    def test_all_profile_values_replay_actual_factual_table_excerpts(self):
        fixtures=json.loads((ROOT/'tests/fixtures/sector_extraction_pages.json').read_text())
        state=json.loads((ROOT/'data/sector_disclosures.json').read_text())
        for profile in self.config['profiles']:
            rows,_,candidates=extract(profile,fixtures[profile['symbol']],profile['seeds'][0],'a'*64,'2026-10-24')
            self.assertFalse(candidates)
            expected={r['id']:(r['value'],r['unit'],r.get('approximate',False)) for r in state['catalogues'][profile['symbol']]['records']}
            self.assertEqual({r['id']:(r['value'],r['unit'],r.get('approximate',False)) for r in rows},expected)

    def test_new_official_download_enters_automatic_reading_without_backdating(self):
        profile=self.config['profiles'][0];config={'profiles':[profile],'max_documents_per_issuer':2}
        previous=json.loads((ROOT/'data/sector_disclosures.json').read_text())
        url='https://tgcc.ma/?jet_download='+'c'*40
        body=('<li>Résultats Semestriels au 30 Juin 2027<a href="'+url+'">Télécharger</a></li>').encode()
        def page(*a,**kw):return body,profile['discovery_pages'][0],'text/html'
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'new.pdf';path.write_bytes(b'%PDF- new-version-fixture')
            with patch('nour.sector_ingestion.pdf_pages',return_value=['TGCC AU 30 JUIN 2027','S1 2027    S1 2026\nCarnet de commandes (M MAD)   29 500       28 360']):
                out=collect(config,previous,{},Path(d),now='2027-10-24T10:00:00+00:00',fetch=lambda *a:path,page_fetch=page)
        catalogue=out['catalogues']['TGCC'];rows={r['id']:r for r in disclosure_view(catalogue,'2027-10-24')['records']}
        self.assertEqual(rows['backlog-2027-06-30']['value'],29500)
        self.assertEqual(rows['backlog-2027-06-30']['status'],'automatic_text_extracted')
        self.assertEqual(rows['backlog-2027-06-30']['available_from'],'2027-10-24')
        self.assertEqual(rows['backlog-2026-06-30']['available_from'],'2026-10-24')
        self.assertFalse(out['candidates'])

    def test_reversed_comparison_columns_are_not_silently_accepted(self):
        p=self.config['profiles'][0]
        rows,_,c=extract(p,['TGCC AU 30 JUIN 2026','S1 2025    S1 2026\nCarnet de commandes (M MAD)  19 100    28 360'],p['seeds'][0],'a'*64,'2026-10-24')
        self.assertFalse(rows);self.assertEqual(c[0]['reason'],'column_period_order_unverified')

    def test_legacy_official_http_link_is_upgraded_without_allowing_other_hosts(self):
        self.assertEqual(discovered_url('http://www.managemgroup.com/report.pdf','https://www.managemgroup.com',['www.managemgroup.com']),'https://www.managemgroup.com/report.pdf')
        self.assertIsNone(discovered_url('http://unapproved.example/report.pdf','https://www.managemgroup.com',['www.managemgroup.com']))

    def test_failed_download_does_not_advance_the_etag_of_an_old_pdf(self):
        from nour.sector_ingestion import download
        import subprocess
        profile=self.config['profiles'][0];url=profile['seeds'][0]
        with tempfile.TemporaryDirectory() as d:
            cache=Path(d);key=hashlib.sha256(url.encode()).hexdigest()
            target=cache/(key+'.pdf');target.write_bytes(b'%PDF- old complete document')
            tag=cache/(key+'.etag');tag.write_text('old-etag')
            def truncated(cmd,**kw):
                Path(cmd[cmd.index('--etag-save')+1]).write_text('new-etag')
                raise subprocess.CalledProcessError(28,cmd)
            with patch('nour.sector_ingestion.subprocess.run',side_effect=truncated):
                with self.assertRaises(subprocess.CalledProcessError):download(url,profile,cache)
            self.assertEqual(tag.read_text(),'old-etag')
            self.assertEqual(target.read_bytes(),b'%PDF- old complete document')
