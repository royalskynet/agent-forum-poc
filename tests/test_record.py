import json
import unittest

from forum_poc.misalign import find_misalignments
from forum_poc.record import build_record, render


def load(name):
    with open(f"fixtures/{name}.json", encoding="utf-8") as f:
        return json.load(f)


def answers():
    with open("fixtures/criteria.json", encoding="utf-8") as f:
        return json.load(f)


class Record(unittest.TestCase):
    def setUp(self):
        self.a, self.b = load("product"), load("eng")
        self.flags = find_misalignments(self.a, self.b)
        self.rec = build_record(self.a, self.b, self.flags, answers())
        self.text = render(self.rec)

    def test_every_flag_appears_in_record(self):
        self.assertEqual(len(self.rec["分歧"]), len(self.flags))

    def test_every_flag_appears_in_rendered_text(self):
        for f in self.flags:
            self.assertIn(f[2], self.text)

    def test_undecided_criterion_listed_with_status(self):
        undecided = [c for c in self.rec["判準"] if c["狀態"] == "未定"]
        self.assertEqual(len(undecided), 1)
        self.assertIn("盡快處理", self.text)

    def test_decided_criteria_marked_ok(self):
        ok = [c for c in self.rec["判準"] if c["狀態"] == "ok"]
        self.assertEqual(len(ok), 2)

    def test_devil_flag_false_when_flags_exist(self):
        self.assertFalse(self.rec["反方觸發"])

    def test_devil_flag_true_when_no_flags(self):
        rec = build_record(self.a, self.a, find_misalignments(self.a, self.a), [])
        self.assertTrue(rec["反方觸發"])

    def test_consensus_items_only_those_without_flags(self):
        self.assertEqual(self.rec["共識項"], [])
        rec = build_record(self.a, self.a, [], [])
        self.assertEqual(rec["共識項"], ["邀請領券"])

    def test_render_returns_nonempty_string(self):
        self.assertTrue(isinstance(self.text, str) and self.text.strip())


if __name__ == "__main__":
    unittest.main()
