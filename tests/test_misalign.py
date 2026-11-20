import json
import unittest

from forum_poc.misalign import find_misalignments


def load(name):
    with open(f"fixtures/{name}.json", encoding="utf-8") as f:
        return json.load(f)


class Misalign(unittest.TestCase):
    def test_planted_misalignment_detected(self):
        flags = find_misalignments(load("product"), load("eng"))
        kinds = {(f[0], f[2]) for f in flags}
        self.assertIn(("範圍錯位", "對帳"), kinds)
        self.assertIn(("範圍錯位", "風控"), kinds)
        self.assertIn(("估時分歧", "2天 vs 15天"), kinds)
        self.assertNotIn(("範圍錯位", "分享連結"), kinds)

    def test_identical_submissions_no_flags(self):
        p = load("product")
        self.assertEqual(find_misalignments(p, p), [])


if __name__ == "__main__":
    unittest.main()
