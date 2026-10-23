import unittest
from tools.assert_nour_scope import check_scope,ALLOWED

class WriteScope(unittest.TestCase):
    def test_only_nour_is_allowed(self):
        self.assertTrue(check_scope(ALLOWED,'https://github.com/'+ALLOWED+'.git'))
        self.assertTrue(check_scope(None,'git@github.com:'+ALLOWED+'.git'))
        for repo,remote in [(ALLOWED,'https://github.com/abdmoutalib207-lang/-bvc-analyzer.git'),
                            ('abdmoutalib207-lang/-bvc-analyzer','https://github.com/'+ALLOWED),
                            (None,'https://example.com/'+ALLOWED)]:
            with self.assertRaises(ValueError):check_scope(repo,remote)
