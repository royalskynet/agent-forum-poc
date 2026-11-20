import json
import unittest

from forum_poc.convergence import should_inject_devil
from forum_poc.misalign import find_misalignments


def load(name):
    with open(f"fixtures/{name}.json", encoding="utf-8") as f:
        return json.load(f)


class Convergence(unittest.TestCase):
    def test_zero_flags_triggers_devil(self):
        p = load("product")
        self.assertTrue(should_inject_devil(find_misalignments(p, p)))

    def test_any_flag_suppresses_devil(self):
        flags = find_misalignments(load("product"), load("eng"))
        self.assertTrue(flags)
        self.assertFalse(should_inject_devil(flags))

    def test_single_flag_suppresses_devil(self):
        self.assertFalse(should_inject_devil([("估時分歧", "x", "1天 vs 9天")]))

    def test_empty_list_triggers_devil(self):
        self.assertTrue(should_inject_devil([]))


if __name__ == "__main__":
    unittest.main()
