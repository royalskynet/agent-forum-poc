import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from forum_poc.charter import attach_labels, build_chartered_agenda, render_chartered
from forum_poc.multi import build_agenda, render_agenda

NAMES = ("compliance", "eng", "english", "product")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def run(path):
    return subprocess.run(
        [sys.executable, "-m", "forum_poc.run_case", path],
        capture_output=True,
        text=True,
        timeout=30,
    )


def tmp_copy(src):
    d = tempfile.mkdtemp()
    shutil.rmtree(d)
    shutil.copytree(src, d)
    return d


class RunCase(unittest.TestCase):
    def tearDown(self):
        for d in getattr(self, "dirs", []):
            shutil.rmtree(d, ignore_errors=True)

    def copy(self, src):
        d = tmp_copy(src)
        self.dirs = getattr(self, "dirs", []) + [d]
        return d

    def test_basic_case_matches_library(self):
        subs = [load(f"examples/case_basic/{n}.json") for n in NAMES]
        want = render_agenda(build_agenda(subs, load("examples/case_basic/criteria.json")))
        r = run("examples/case_basic")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, want)

    def test_full_case_matches_library(self):
        labels = load("examples/case_full/labels.json")
        subs = []
        for n in NAMES:
            s = load(f"examples/case_full/{n}.json")
            subs.append(attach_labels(s, labels[n]) if n in labels else s)
        rec = build_chartered_agenda(
            subs,
            load("examples/case_full/charters.json"),
            load("examples/case_full/criteria.json"),
            load("examples/case_full/commitments.json"),
        )
        r = run("examples/case_full")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, render_chartered(rec))
        self.assertIn("待答題總數：7", r.stdout)
        self.assertNotIn("隱私同意", r.stdout)

    def test_two_parties_only_no_criteria_file(self):
        d = self.copy("examples/case_basic")
        os.remove(d + "/criteria.json")
        os.remove(d + "/compliance.json")
        os.remove(d + "/english.json")
        r = run(d)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("各方：eng、product", r.stdout)

    def test_unknown_extra_party_file_is_picked_up(self):
        d = self.copy("examples/case_basic")
        extra = load(d + "/product.json")
        extra["party"] = "ops"
        with open(d + "/ops.json", "w", encoding="utf-8") as f:
            json.dump(extra, f, ensure_ascii=False)
        r = run(d)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ops", r.stdout.split("爭議：")[0])

    def test_labels_without_charters_fails_loud(self):
        d = self.copy("examples/case_basic")
        shutil.copy("examples/case_full/labels.json", d + "/labels.json")
        r = run(d)
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("charters.json", r.stderr)

    def test_commitments_without_charters_fails_loud(self):
        d = self.copy("examples/case_basic")
        shutil.copy("examples/case_full/commitments.json", d + "/commitments.json")
        r = run(d)
        self.assertEqual(r.returncode, 2)
        self.assertIn("charters.json", r.stderr)

    def test_bad_inputs_exit_2_without_traceback(self):
        empty = tempfile.mkdtemp()
        self.dirs = getattr(self, "dirs", []) + [empty]
        bad_json = self.copy("examples/case_basic")
        with open(bad_json + "/eng.json", "w", encoding="utf-8") as f:
            f.write("{not json")
        invalid = self.copy("examples/case_basic")
        s = load(invalid + "/eng.json")
        del s["items"]["邀請領券"]["估時_天"]
        with open(invalid + "/eng.json", "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False)
        for path in (empty, "/nonexistent-dir-xyz", bad_json, invalid):
            r = run(path)
            self.assertEqual(r.returncode, 2, path)
            self.assertNotIn("Traceback", r.stderr, path)
            self.assertTrue(r.stderr.strip(), path)
            self.assertEqual(r.stdout, "", path)

    def test_labels_not_a_dict_or_unknown_party_fails_loud(self):
        for bad in ([], {"ghost": {"邀請領券": {"隱私同意": "機密"}}}):
            d = self.copy("examples/case_full")
            with open(d + "/labels.json", "w", encoding="utf-8") as f:
                json.dump(bad, f, ensure_ascii=False)
            r = run(d)
            self.assertEqual(r.returncode, 2, bad)
            self.assertEqual(r.stdout, "", bad)
            self.assertIn("labels.json", r.stderr, bad)

    def test_inline_label_in_submission_fails_loud(self):
        for case in ("examples/case_basic", "examples/case_full"):
            d = self.copy(case)
            s = load(d + "/eng.json")
            s["items"]["邀請領券"]["標籤"] = {"對账": "機密"}
            with open(d + "/eng.json", "w", encoding="utf-8") as f:
                json.dump(s, f, ensure_ascii=False)
            r = run(d)
            self.assertEqual(r.returncode, 2, case)
            self.assertEqual(r.stdout, "", case)
            self.assertIn("labels.json", r.stderr, case)
            self.assertIn("eng.json", r.stderr, case)

    def test_unknown_keys_anywhere_in_submission_fail_loud(self):
        def top(s):
            s["標籤"] = {"對帳": "機密"}

        def variant(s):
            s["items"]["邀請領券"]["標簽"] = {"對帳": "機密"}

        def extra_field(s):
            s["items"]["邀請領券"]["備註"] = "x"

        for case in ("examples/case_basic", "examples/case_full"):
            for mutate in (top, variant, extra_field):
                d = self.copy(case)
                s = load(d + "/eng.json")
                mutate(s)
                with open(d + "/eng.json", "w", encoding="utf-8") as f:
                    json.dump(s, f, ensure_ascii=False)
                r = run(d)
                self.assertEqual(r.returncode, 2, (case, mutate.__name__))
                self.assertEqual(r.stdout, "", (case, mutate.__name__))
                self.assertIn("eng.json", r.stderr, (case, mutate.__name__))

    def test_duplicate_keys_in_any_input_file_fail_loud(self):
        dup_texts = {
            "labels.json": [
                '{"compliance":{"邀請領券":{"隱私同意":"機密"}},"compliance":{}}',
                '{"compliance":{"邀請領券":{"隱私同意":"機密"},"邀請領券":{}}}',
                '{"compliance":{"邀請領券":{"隱私同意":"機密","隱私同意":"內部"}}}',
            ],
            "charters.json": ['[{"party":"product","party":"eng","可揭露":[],"可承諾":{},"禁止承諾":[]}]'],
        }
        for name, texts in dup_texts.items():
            for text in texts:
                d = self.copy("examples/case_full")
                with open(f"{d}/{name}", "w", encoding="utf-8") as f:
                    f.write(text)
                r = run(d)
                self.assertEqual(r.returncode, 2, text)
                self.assertEqual(r.stdout, "", text)
                self.assertIn(name, r.stderr, text)
                self.assertNotIn("Traceback", r.stderr, text)
        d = self.copy("examples/case_basic")
        with open(d + "/eng.json", "w", encoding="utf-8") as f:
            f.write('{"party":"eng","party":"eng","items":{}}')
        r = run(d)
        self.assertEqual(r.returncode, 2)
        self.assertIn("eng.json", r.stderr)

    def test_reserved_name_with_other_case_fails_loud(self):
        d = self.copy("examples/case_full")
        os.rename(d + "/labels.json", d + "/Labels.JSON")
        r = run(d)
        self.assertEqual(r.returncode, 2)
        self.assertEqual(r.stdout, "")
        self.assertIn("Labels.JSON", r.stderr)

    def test_criteria_and_commitments_must_be_lists(self):
        for name, case in (("criteria.json", "examples/case_basic"), ("commitments.json", "examples/case_full")):
            d = self.copy(case)
            with open(f"{d}/{name}", "w", encoding="utf-8") as f:
                json.dump({}, f)
            r = run(d)
            self.assertEqual(r.returncode, 2, name)
            self.assertEqual(r.stdout, "", name)
            self.assertIn(name, r.stderr, name)

    def test_broken_json_names_the_file(self):
        d = self.copy("examples/case_basic")
        with open(d + "/eng.json", "w", encoding="utf-8") as f:
            f.write("{not json")
        r = run(d)
        self.assertEqual(r.returncode, 2)
        self.assertIn("eng.json", r.stderr)

    def test_file_name_order_does_not_change_output(self):
        d = self.copy("examples/case_basic")
        first = run(d)
        self.assertEqual(first.returncode, 0, first.stderr)
        want = first.stdout
        self.assertIn("待答題總數", want)
        for n in NAMES:
            os.rename(f"{d}/{n}.json", f"{d}/z_{n}.json")
        again = run(d)
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertEqual(again.stdout, want)


if __name__ == "__main__":
    unittest.main()
