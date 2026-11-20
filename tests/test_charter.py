import copy
import json
import unittest

from forum_poc.charter import (
    apply_charter,
    attach_labels,
    build_chartered_agenda,
    check_commitment,
    render_chartered,
    validate_charter,
)
from forum_poc.multi import build_agenda

NAMES = ("product", "eng", "compliance", "english")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def four():
    return [load(f"fixtures/multi/{n}.json") for n in NAMES]


def criteria():
    return load("fixtures/criteria.json")


def charters():
    return load("fixtures/charter/charters.json")


def commitments():
    return load("fixtures/charter/commitments.json")


def labelled_four():
    labels = load("fixtures/charter/labels.json")
    return [attach_labels(s, labels[s["party"]]) if s["party"] in labels else s for s in four()]


def item(inc=(), exc=(), assume=(), dep=(), est=1, labels=None):
    it = {"含": list(inc), "不含": list(exc), "假設": list(assume), "估時_天": est, "依賴": list(dep)}
    if labels is not None:
        it["標籤"] = labels
    return it


def charter(party, show=("公開", "內部"), can=None, forbid=()):
    return {"party": party, "可揭露": list(show), "可承諾": can or {}, "禁止承諾": list(forbid)}


class CharterValidation(unittest.TestCase):
    def test_fixture_charters_valid(self):
        for c in charters():
            self.assertEqual(validate_charter(c), [], c)

    def test_empty_disclosure_list_is_allowed(self):
        self.assertEqual(validate_charter(charter("a", show=())), [])

    def test_unknown_label_in_disclosure_rejected(self):
        self.assertTrue(validate_charter(charter("a", show=("公開", "亂寫"))))

    def test_bad_caps_rejected(self):
        for bad in (0, -1, True, "5"):
            c = charter("a", can={"x": {"估時_天_上限": bad}})
            self.assertTrue(validate_charter(c), bad)

    def test_item_both_allowed_and_forbidden_rejected(self):
        c = charter("a", can={"x": {"估時_天_上限": 5}}, forbid=("x",))
        self.assertTrue(any("x" in e for e in validate_charter(c)))

    def test_missing_keys_and_bad_types_rejected(self):
        self.assertTrue(validate_charter(charter("")))
        c = charter("a")
        del c["可承諾"]
        self.assertTrue(validate_charter(c))
        c = charter("a")
        c["可揭露"] = "公開"
        self.assertTrue(validate_charter(c))
        self.assertTrue(validate_charter("not a dict"))

    def test_validation_does_not_mutate(self):
        c = charters()[0]
        snapshot = copy.deepcopy(c)
        validate_charter(c)
        self.assertEqual(c, snapshot)


class ApplyCharter(unittest.TestCase):
    def setUp(self):
        self.sub = {
            "party": "a",
            "items": {
                "x": item(
                    inc=["公開工作", "內部工作", "SECRET機密工作"],
                    exc=["SECRET排除項"],
                    assume=["內部假設"],
                    dep=["SECRETDEP"],
                    labels={
                        "公開工作": "公開",
                        "SECRET機密工作": "機密",
                        "SECRET排除項": "機密",
                        "SECRETDEP": "機密",
                    },
                )
            },
        }

    def test_secret_texts_removed_and_not_leaked(self):
        visible, withheld = apply_charter(self.sub, charter("a"))
        self.assertEqual(visible["items"]["x"]["含"], ["公開工作", "內部工作"])
        self.assertEqual(visible["items"]["x"]["不含"], [])
        self.assertEqual(visible["items"]["x"]["依賴"], [])
        self.assertEqual(visible["items"]["x"]["假設"], ["內部假設"])
        self.assertNotIn("SECRET", repr(visible))
        self.assertNotIn("SECRET", repr(withheld))
        self.assertEqual(len(withheld), 3)

    def test_unknown_label_withheld_even_if_charter_lists_it(self):
        sub = {"party": "a", "items": {"x": item(inc=["w"], labels={"w": "絕密"})}}
        c = charter("a", show=("公開", "內部", "機密"))
        c["可揭露"].append("絕密")
        visible, withheld = apply_charter(sub, c)
        self.assertEqual(visible["items"]["x"]["含"], [])
        self.assertEqual(len(withheld), 1)

    def test_label_map_not_exposed(self):
        visible, _ = apply_charter(self.sub, charter("a"))
        self.assertNotIn("標籤", visible["items"]["x"])

    def test_unlabelled_text_counts_as_internal(self):
        visible, _ = apply_charter(self.sub, charter("a", show=("公開",)))
        self.assertEqual(visible["items"]["x"]["含"], ["公開工作"])
        self.assertEqual(visible["items"]["x"]["假設"], [])

    def test_unknown_label_fails_closed(self):
        sub = {"party": "a", "items": {"x": item(inc=["w"], labels={"w": "亂寫"})}}
        visible, withheld = apply_charter(sub, charter("a", show=("公開", "內部", "機密")))
        self.assertEqual(visible["items"]["x"]["含"], [])
        self.assertEqual(len(withheld), 1)

    def test_input_not_mutated(self):
        snapshot = copy.deepcopy(self.sub)
        apply_charter(self.sub, charter("a"))
        self.assertEqual(self.sub, snapshot)

    def test_party_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            apply_charter(self.sub, charter("b"))

    def test_attach_labels_unknown_item_rejected(self):
        with self.assertRaises(ValueError):
            attach_labels(self.sub, {"nope": {"w": "機密"}})

    def test_attach_labels_text_not_in_item_rejected(self):
        with self.assertRaises(ValueError):
            attach_labels(self.sub, {"x": {"打錯字的工作": "機密"}})

    def test_attach_labels_bad_label_value_rejected(self):
        with self.assertRaises(ValueError):
            attach_labels(self.sub, {"x": {"內部工作": "亂寫"}})

    def test_attach_labels_merges_and_new_wins(self):
        out = attach_labels(self.sub, {"x": {"內部工作": "機密", "公開工作": "內部"}})
        got = out["items"]["x"]["標籤"]
        self.assertEqual(got["內部工作"], "機密")
        self.assertEqual(got["公開工作"], "內部")
        self.assertEqual(got["SECRETDEP"], "機密")

    def test_attach_labels_does_not_mutate(self):
        snapshot = copy.deepcopy(self.sub)
        attach_labels(self.sub, {"x": {"內部工作": "機密"}})
        self.assertEqual(self.sub, snapshot)


class CheckCommitment(unittest.TestCase):
    def setUp(self):
        self.c = charter("a", can={"x": {"估時_天_上限": 10}}, forbid=("y",))

    def test_within_cap_including_equal(self):
        self.assertEqual(check_commitment(self.c, "x", 10), "可承諾")
        self.assertEqual(check_commitment(self.c, "x", 3), "可承諾")

    def test_over_cap_needs_human(self):
        self.assertEqual(check_commitment(self.c, "x", 10.5), "須回問人")

    def test_unlisted_item_needs_human(self):
        self.assertEqual(check_commitment(self.c, "z", 1), "須回問人")

    def test_forbidden_item(self):
        self.assertEqual(check_commitment(self.c, "y", 1), "禁止")

    def test_bad_days_rejected(self):
        for bad in (0, -2, True, "3", None):
            with self.assertRaises(ValueError):
                check_commitment(self.c, "x", bad)


class ChartedAgenda(unittest.TestCase):
    def setUp(self):
        self.rec = build_chartered_agenda(labelled_four(), charters(), criteria(), commitments())
        self.text = render_chartered(self.rec)

    def test_withheld_summary_has_counts_not_texts(self):
        self.assertEqual(
            self.rec["遮蔽"],
            [
                {"party": "compliance", "議程項目": "邀請領券", "欄位": "含", "標籤": "機密", "數量": 1},
                {"party": "eng", "議程項目": "邀請領券", "欄位": "依賴", "標籤": "機密", "數量": 1},
            ],
        )

    def test_withheld_texts_never_appear(self):
        for secret in ("隱私同意", "風控接口"):
            self.assertNotIn(secret, repr(self.rec))
            self.assertNotIn(secret, self.text)

    def test_commitment_results(self):
        got = [(c["party"], c["議程項目"], c["估時_天"], c["結果"]) for c in self.rec["承諾檢查"]]
        self.assertEqual(
            got,
            [
                ("compliance", "邀請領券", 5, "禁止"),
                ("eng", "邀請領券", 20, "須回問人"),
                ("english", "英文落地頁", 2, "可承諾"),
                ("english", "邀請領券", 2, "須回問人"),
                ("product", "邀請領券", 8, "可承諾"),
            ],
        )

    def test_questions_are_disputes_plus_criteria_plus_human_checks(self):
        self.assertEqual(len(self.rec["爭議"]), 4)
        self.assertEqual(len(self.rec["待答題"]), 7)
        human = [q for q in self.rec["待答題"] if "主人需確認" in q]
        self.assertEqual(len(human), 2)
        self.assertTrue(any("eng" in q and "邀請領券" in q and "20" in q for q in human))
        self.assertTrue(any("english" in q and "邀請領券" in q for q in human))

    def test_redaction_removes_the_hidden_dispute(self):
        contents = {d["內容"] for d in self.rec["爭議"]}
        self.assertNotIn("隱私同意", contents)
        self.assertIn("對帳", contents)

    def test_render_has_sections_and_total(self):
        self.assertIn("待答題總數：7", self.text)
        self.assertIn("遮蔽：", self.text)
        self.assertIn("承諾檢查：", self.text)
        self.assertIn("禁止", self.text)
        self.assertIn("須回問人", self.text)
        for q in self.rec["待答題"]:
            self.assertIn(q, self.text)

    def test_open_charters_match_plain_agenda(self):
        open_charters = [charter(n, show=("公開", "內部", "機密")) for n in NAMES]
        base = build_agenda(four(), criteria())
        rec = build_chartered_agenda(four(), open_charters, criteria(), [])
        for key in ("共識項", "爭議", "判準", "待答題", "反方觸發"):
            self.assertEqual(rec[key], base[key], key)
        self.assertEqual(rec["遮蔽"], [])
        self.assertEqual(rec["承諾檢查"], [])

    def test_secret_never_reaches_record_or_text(self):
        subs = [
            {"party": "a", "items": {"x": item(inc=["w", "SECRETWORK"], dep=["SECRETDEP"], est=2, labels={"SECRETWORK": "機密", "SECRETDEP": "機密"})}},
            {"party": "b", "items": {"x": item(inc=["w"], est=9)}},
        ]
        cs = [charter("a"), charter("b")]
        rec = build_chartered_agenda(subs, cs, [], [])
        self.assertNotIn("SECRET", repr(rec))
        self.assertNotIn("SECRET", render_chartered(rec))
        self.assertEqual(sum(g["數量"] for g in rec["遮蔽"]), 2)

    def test_withheld_count_aggregates_same_group(self):
        subs = [
            {"party": "a", "items": {"x": item(inc=["w", "S1", "S2", "S3"], est=2, labels={"S1": "機密", "S2": "機密", "S3": "機密"})}},
            {"party": "b", "items": {"x": item(inc=["w"], est=2)}},
        ]
        rec = build_chartered_agenda(subs, [charter("a"), charter("b")], [], [])
        self.assertEqual(
            rec["遮蔽"],
            [{"party": "a", "議程項目": "x", "欄位": "含", "標籤": "機密", "數量": 3}],
        )

    def test_order_independent(self):
        subs, cs = labelled_four(), charters()
        base = render_chartered(build_chartered_agenda(subs, cs, criteria(), commitments()))
        again = render_chartered(
            build_chartered_agenda(list(reversed(subs)), list(reversed(cs)), criteria(), list(reversed(commitments())))
        )
        self.assertEqual(again, base)

    def test_inputs_not_mutated(self):
        subs, cs, cm = labelled_four(), charters(), commitments()
        snapshots = copy.deepcopy((subs, cs, cm))
        build_chartered_agenda(subs, cs, criteria(), cm)
        self.assertEqual((subs, cs, cm), snapshots)

    def test_duplicate_charter_for_same_party_rejected(self):
        wide = charters()
        narrow = copy.deepcopy(wide[0])
        narrow["可揭露"] = []
        for order in (wide + [narrow], [narrow] + wide):
            with self.assertRaises(ValueError):
                build_chartered_agenda(labelled_four(), order, criteria(), [])

    def test_same_party_item_commitments_order_independent(self):
        cm = [
            {"party": "product", "議程項目": "邀請領券", "估時_天": 9},
            {"party": "product", "議程項目": "邀請領券", "估時_天": 3},
        ]
        a = build_chartered_agenda(labelled_four(), charters(), criteria(), cm)
        b = build_chartered_agenda(labelled_four(), charters(), criteria(), list(reversed(cm)))
        self.assertEqual(a["承諾檢查"], b["承諾檢查"])
        self.assertEqual(a["待答題"], b["待答題"])
        self.assertEqual([c["估時_天"] for c in a["承諾檢查"]], [3, 9])

    def test_missing_or_extra_charter_rejected(self):
        with self.assertRaises(ValueError):
            build_chartered_agenda(labelled_four(), charters()[:3], criteria(), [])
        with self.assertRaises(ValueError):
            build_chartered_agenda(labelled_four(), charters() + [charter("ghost")], criteria(), [])

    def test_invalid_charter_rejected(self):
        cs = charters()
        cs[0]["可揭露"] = ["亂寫"]
        with self.assertRaises(ValueError):
            build_chartered_agenda(labelled_four(), cs, criteria(), [])

    def test_commitment_for_unknown_party_or_item_rejected(self):
        for bad in (
            {"party": "ghost", "議程項目": "邀請領券", "估時_天": 1},
            {"party": "product", "議程項目": "不存在", "估時_天": 1},
            {"party": "product", "議程項目": "邀請領券", "估時_天": 0},
        ):
            with self.assertRaises(ValueError):
                build_chartered_agenda(labelled_four(), charters(), criteria(), [bad])


if __name__ == "__main__":
    unittest.main()
