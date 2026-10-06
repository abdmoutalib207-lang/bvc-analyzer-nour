import json
from pathlib import Path
import unittest

from tools.ecc import ROOT, expected_links, verify_sources


class ECCIntegration(unittest.TestCase):
    def test_pinned_originals_license_and_repository_local_bindings(self):
        manifest=json.loads((ROOT/'vendor/ecc/manifest.json').read_text())
        verify_sources(manifest)
        self.assertEqual(manifest['skill_count'],8)
        self.assertEqual(manifest['agent_count'],3)
        self.assertFalse(manifest['automatic_hooks'])
        self.assertIn('MIT License',(ROOT/'vendor/ecc/LICENSE').read_text())
        for relative,target in expected_links(manifest).items():
            link=ROOT/relative
            self.assertTrue(link.is_symlink())
            self.assertEqual(link.resolve(),target.resolve())
            self.assertTrue(target.resolve().is_relative_to(ROOT/'vendor/ecc'))

    def test_altered_digest_and_unsafe_paths_are_rejected(self):
        manifest=json.loads((ROOT/'vendor/ecc/manifest.json').read_text())
        manifest['files'][0]['sha256']='0'*64
        with self.assertRaises(ValueError):
            verify_sources(manifest)
        manifest['files'][0]['path']='../../README.md'
        with self.assertRaises(ValueError):
            verify_sources(manifest)


if __name__=='__main__':
    unittest.main()
