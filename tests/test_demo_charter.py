import subprocess
import sys
import unittest


class DemoCharter(unittest.TestCase):
    def test_demo_runs_and_hides_secrets(self):
        r = subprocess.run(
            [sys.executable, "-m", "forum_poc.demo_charter"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        for needle in ("待答題總數：7", "遮蔽：", "承諾檢查：", "禁止", "須回問人", "對帳"):
            self.assertIn(needle, r.stdout)
        for secret in ("隱私同意", "風控接口"):
            self.assertNotIn(secret, r.stdout)


if __name__ == "__main__":
    unittest.main()
