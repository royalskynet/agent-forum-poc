import subprocess
import sys
import unittest


class DemoMulti(unittest.TestCase):
    def test_demo_runs_and_prints_agenda(self):
        r = subprocess.run(
            [sys.executable, "-m", "forum_poc.demo_multi"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        for needle in ("待答題總數：6", "對帳", "隱私同意", "english", "compliance"):
            self.assertIn(needle, r.stdout)


if __name__ == "__main__":
    unittest.main()
