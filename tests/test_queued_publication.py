from pathlib import Path
import unittest

from nour.runtime import source_commit

ROOT = Path(__file__).resolve().parents[1]


class QueuedPublication(unittest.TestCase):
    def test_actual_checked_out_commit_takes_priority_over_old_event(self):
        actual='b'*40
        queued='a'*40
        self.assertEqual(source_commit({'NOUR_CODE_COMMIT':actual,'GITHUB_SHA':queued}),actual)
        self.assertEqual(source_commit({'GITHUB_SHA':queued}),queued)
        self.assertEqual(source_commit({'NOUR_CODE_COMMIT':'','GITHUB_SHA':queued}),queued)
        self.assertEqual(source_commit({}),'')

    def test_daily_checkout_is_current_main_and_publication_never_forces_push(self):
        workflow=(ROOT/'.github/workflows/nour_daily.yml').read_text()
        checkout=workflow.split('- uses: actions/checkout@v4',1)[1].split('- name:',1)[0]
        self.assertIn('ref: main',checkout)
        self.assertIn('NOUR_CODE_COMMIT=$(git rev-parse HEAD)',workflow)
        self.assertIn('cancel-in-progress: false',workflow)
        self.assertNotIn('git push --force',workflow)
        self.assertIn('commit=source_commit(os.environ)',(ROOT/'run.py').read_text())


if __name__ == '__main__':
    unittest.main()
