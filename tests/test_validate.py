import copy
import json
import unittest

from forum_poc.validate import validate_pair, validate_submission


def load(name):
    with open(f"fixtures/{name}.json", encoding="utf-8") as f:
        return json.load(f)


class ValidateSubmission(unittest.TestCase):
    def test_valid_fixture_has_no_errors(self):
        self.assertEqual(validate_submission(load("product")), [])

    def test_missing_field_rejected(self):
        s = load("product")
        del s["items"]["邀請領券"]["估時_天"]
        self.assertTrue(validate_submission(s))

    def test_zero_estimate_rejected(self):
        s = load("product")
        s["items"]["邀請領券"]["估時_天"] = 0
        self.assertTrue(validate_submission(s))

    def test_negative_estimate_rejected(self):
        s = load("product")
        s["items"]["邀請領券"]["估時_天"] = -3
        self.assertTrue(validate_submission(s))

    def test_empty_items_rejected(self):
        s = load("product")
        s["items"] = {}
        self.assertTrue(validate_submission(s))

    def test_missing_party_rejected(self):
        s = load("product")
        del s["party"]
        self.assertTrue(validate_submission(s))

    def test_list_field_with_wrong_type_rejected(self):
        s = load("product")
        s["items"]["邀請領券"]["含"] = "分享連結"
        self.assertTrue(validate_submission(s))


class ValidatePair(unittest.TestCase):
    def test_matching_pair_ok(self):
        self.assertEqual(validate_pair(load("product"), load("eng")), [])

    def test_one_sided_item_rejected(self):
        a, b = load("product"), load("eng")
        b["items"]["額外項目"] = copy.deepcopy(b["items"]["邀請領券"])
        self.assertTrue(validate_pair(a, b))

    def test_same_party_name_rejected(self):
        a = load("product")
        b = copy.deepcopy(a)
        self.assertTrue(validate_pair(a, b))


if __name__ == "__main__":
    unittest.main()
