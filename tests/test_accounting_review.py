import tempfile
from pathlib import Path
import unittest

from tools.prepare_accounting_review import candidate_pages, prepare, selected_records


class AccountingReview(unittest.TestCase):
    def test_unknown_or_unbounded_batch_is_refused(self):
        for symbols in ([],['UNKNOWN'],[str(n) for n in range(13)]):
            with self.assertRaises(ValueError):selected_records({'BCP':{}},symbols)
        self.assertEqual(selected_records({'BCP':{}},['BCP','BCP']),[('BCP',{})])

    def test_layout_matches_are_candidates_not_reviewed_facts(self):
        pages=candidate_pages(['Notice','Référentiel IFRS\nPrincipes comptables','Juste valeur'])
        self.assertEqual(pages[0]['page'],2)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'source.pdf';source.write_bytes(b'%PDF-test')
            result=prepare('BCP',{'url':'https://www.ammc.ma/test.pdf','exercice':2025},root,root,
                fetch=lambda *a:source,reader=lambda p:['Référentiel IFRS'])
            self.assertEqual(result['status'],'candidate_only')
            self.assertFalse(result['visual_review']);self.assertFalse(result['used_for_score'])
            self.assertEqual(len(result['sha256']),64)

    def test_source_failure_is_local_and_does_not_leak_response_text(self):
        def fail(*a):raise OSError('private response must not enter evidence')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);result=prepare('BCP',{'url':'https://www.ammc.ma/test.pdf'},root,root,fetch=fail)
            self.assertEqual(result['status'],'unavailable')
            self.assertEqual(result['failure_class'],'OSError')
            self.assertNotIn('private',str(result))
