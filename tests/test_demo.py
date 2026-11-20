import subprocess
import sys
import unittest


class Demo(unittest.TestCase):
    def test_demo_runs_and_prints_record(self):
        r = subprocess.run(
            [sys.executable, "-m", "forum_poc.demo"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        for needle in ("對帳", "風控", "盡快處理", "分歧"):
            self.assertIn(needle, r.stdout)


if __name__ == "__main__":
    unittest.main()
