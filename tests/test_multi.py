import copy
import itertools
import json
import unittest

from forum_poc.misalign import find_misalignments
from forum_poc.multi import build_agenda, find_disputes, render_agenda, validate_multi

NAMES = ("product", "eng", "compliance", "english")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def four():
    return [load(f"fixtures/multi/{n}.json") for n in NAMES]


def criteria():
    return load("fixtures/criteria.json")


def sub(party, items):
    return {"party": party, "items": items}


def item(inc=(), exc=(), est=1):
    return {"含": list(inc), "不含": list(exc), "假設": [], "估時_天": est, "依賴": []}


class Validation(unittest.TestCase):
    def test_four_party_fixture_valid(self):
        self.assertEqual(validate_multi(four()), [])

    def test_null_estimate_allowed(self):
        subs = [sub("a", {"x": item(est=None)}), sub("b", {"x": item(est=10)})]
        self.assertEqual(validate_multi(subs), [])

    def test_missing_estimate_key_rejected(self):
        subs = [sub("a", {"x": item()}), sub("b", {"x": item()})]
        del subs[0]["items"]["x"]["估時_天"]
        self.assertTrue(validate_multi(subs))

    def test_zero_negative_and_bool_estimate_rejected(self):
        for bad in (0, -3, True):
            subs = [sub("a", {"x": item(est=bad)}), sub("b", {"x": item()})]
            self.assertTrue(validate_multi(subs), bad)

    def test_single_party_rejected(self):
        self.assertTrue(validate_multi(four()[:1]))

    def test_duplicate_party_rejected(self):
        p = four()[0]
        self.assertTrue(validate_multi([p, copy.deepcopy(p)]))

    def test_one_sided_item_names_item_and_party(self):
        subs = four()
        del subs[3]["items"]["英文落地頁"]
        errors = validate_multi(subs)
        self.assertTrue(any("英文落地頁" in e and "english" in e for e in errors), errors)

    def test_include_and_exclude_same_work_item_rejected(self):
        subs = [sub("a", {"x": item(inc=["w"], exc=["w"])}), sub("b", {"x": item()})]
        errors = validate_multi(subs)
        self.assertTrue(any("w" in e for e in errors), errors)

    def test_missing_list_field_rejected(self):
        subs = [sub("a", {"x": item()}), sub("b", {"x": item()})]
        del subs[1]["items"]["x"]["含"]
        self.assertTrue(validate_multi(subs))


class Disputes(unittest.TestCase):
    def test_counts_and_kinds(self):
        disputes = find_disputes(four())
        kinds = sorted(d["種類"] for d in disputes)
        self.assertEqual(kinds, ["估時分歧"] + ["範圍錯位"] * 4)

    def test_stances_for_contested_work_item(self):
        d = next(x for x in find_disputes(four()) if x["內容"] == "對帳")
        self.assertEqual(d["種類"], "範圍錯位")
        self.assertEqual(d["議程項目"], "邀請領券")
        self.assertEqual(
            d["立場"],
            {"eng": "含", "product": "未提及", "compliance": "明確排除", "english": "未提及"},
        )

    def test_one_dispute_per_item_and_work_item(self):
        keys = [(d["種類"], d["議程項目"], d["內容"]) for d in find_disputes(four())]
        self.assertEqual(len(keys), len(set(keys)))

    def test_agreed_work_item_not_disputed(self):
        contents = {d["內容"] for d in find_disputes(four())}
        self.assertNotIn("領券", contents)
        self.assertNotIn("英文文案", contents)

    def test_estimate_dispute_ignores_null_party(self):
        d = next(x for x in find_disputes(four()) if x["種類"] == "估時分歧")
        self.assertEqual(d["內容"], "2天 vs 15天")
        self.assertEqual(d["立場"], {"product": 2, "eng": 15, "english": 3})

    def test_null_estimate_never_triggers_estimate_dispute(self):
        subs = [sub("a", {"x": item(inc=["w"], est=None)}), sub("b", {"x": item(inc=["w"], est=10)})]
        self.assertEqual(find_disputes(subs), [])

    def test_all_null_estimates_no_crash(self):
        subs = [sub("a", {"x": item(est=None)}), sub("b", {"x": item(est=None)})]
        self.assertEqual(find_disputes(subs), [])

    def test_three_party_stances(self):
        subs = [
            sub("a", {"x": item(inc=["w"])}),
            sub("b", {"x": item(exc=["w"])}),
            sub("c", {"x": item(inc=["w"])}),
        ]
        disputes = find_disputes(subs)
        self.assertEqual(len(disputes), 1)
        self.assertEqual(disputes[0]["立場"], {"a": "含", "b": "明確排除", "c": "含"})
        agreed = [sub(p, {"x": item(inc=["w"])}) for p in "abc"]
        self.assertEqual(find_disputes(agreed), [])

    def test_two_party_result_matches_pairwise_function(self):
        p, e = load("fixtures/product.json"), load("fixtures/eng.json")
        old = {(f[0], f[1], f[2]) for f in find_misalignments(p, e)}
        new = {(d["種類"], d["議程項目"], d["內容"]) for d in find_disputes([p, e])}
        self.assertTrue(old)
        self.assertEqual(old, new)

    def test_fewer_disputes_than_pairwise_scope_flags(self):
        pairwise = 0
        for a, b in itertools.combinations(four(), 2):
            for s in (a, b):
                for it in s["items"].values():
                    if it["估時_天"] is None:
                        it["估時_天"] = 1
            pairwise += len([f for f in find_misalignments(a, b) if f[0] == "範圍錯位"])
        scope = [d for d in find_disputes(four()) if d["種類"] == "範圍錯位"]
        self.assertEqual(pairwise, 13)
        self.assertEqual(len(scope), 4)

    def test_submission_order_does_not_matter(self):
        subs = four()
        base = build_agenda(subs, criteria())
        self.assertEqual(build_agenda(list(reversed(subs)), criteria()), base)
        self.assertEqual(build_agenda(subs[2:] + subs[:2], criteria()), base)
        self.assertEqual(render_agenda(build_agenda(list(reversed(subs)), criteria())), render_agenda(base))

    def test_inputs_not_mutated(self):
        subs = four()
        snapshot = copy.deepcopy(subs)
        build_agenda(subs, criteria())
        self.assertEqual(subs, snapshot)


class Agenda(unittest.TestCase):
    def setUp(self):
        self.rec = build_agenda(four(), criteria())
        self.text = render_agenda(self.rec)

    def test_consensus_items(self):
        self.assertEqual(self.rec["共識項"], ["英文落地頁"])

    def test_one_question_per_dispute_plus_undecided_criteria(self):
        undecided = [c for c in self.rec["判準"] if c["狀態"] == "未定"]
        self.assertEqual(len(undecided), 1)
        self.assertEqual(len(self.rec["爭議"]), 5)
        self.assertEqual(len(self.rec["待答題"]), 6)

    def test_every_dispute_is_asked(self):
        for d in self.rec["爭議"]:
            self.assertTrue(
                any(d["議程項目"] in q and d["內容"] in q for q in self.rec["待答題"]),
                d,
            )

    def test_undecided_criterion_is_asked(self):
        self.assertTrue(any("沒有風控上線可接受的最大損失" in q for q in self.rec["待答題"]))

    def test_questions_far_fewer_than_pairwise_flags(self):
        self.assertLess(len(self.rec["待答題"]), 13)

    def test_devil_not_triggered_when_disputes_exist(self):
        self.assertIs(self.rec["反方觸發"], False)

    def test_zero_disputes_triggers_devil(self):
        subs = [sub(p, {"x": item(inc=["w"], est=2)}) for p in ("a", "b", "c")]
        rec = build_agenda(subs, [])
        self.assertEqual(rec["爭議"], [])
        self.assertEqual(rec["待答題"], [])
        self.assertEqual(rec["共識項"], ["x"])
        self.assertIs(rec["反方觸發"], True)

    def test_render_contains_everything(self):
        self.assertIn("待答題總數：6", self.text)
        for d in self.rec["爭議"]:
            self.assertIn(d["內容"], self.text)
        for q in self.rec["待答題"]:
            self.assertIn(q, self.text)
        for name in NAMES:
            self.assertIn(name, self.text)
        self.assertIn("盡快處理", self.text)


if __name__ == "__main__":
    unittest.main()
