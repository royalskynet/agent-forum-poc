import unittest

from forum_poc.criteria import check_answer


class CheckAnswer(unittest.TestCase):
    def test_number_with_unit_ok(self):
        self.assertEqual(check_answer("硬性限制", "週三前，約 5 天")[0], "ok")

    def test_budget_with_currency_ok(self):
        self.assertEqual(check_answer("預算", "上限 50000 元")[0], "ok")

    def test_vague_answer_undecided(self):
        self.assertEqual(check_answer("預算", "盡快處理")[0], "未定")

    def test_number_without_unit_undecided(self):
        self.assertEqual(check_answer("硬性限制", "大概 5")[0], "未定")

    def test_empty_answer_undecided(self):
        self.assertEqual(check_answer("硬性限制", "")[0], "未定")

    def test_acceptance_with_artifact_and_signer_ok(self):
        self.assertEqual(check_answer("驗收標準", "產物：驗收清單 v1；簽核：營運主管")[0], "ok")

    def test_acceptance_missing_signer_undecided(self):
        self.assertEqual(check_answer("驗收標準", "產物：驗收清單 v1")[0], "未定")

    def test_acceptance_missing_artifact_undecided(self):
        self.assertEqual(check_answer("驗收標準", "簽核：營運主管")[0], "未定")

    def test_unknown_kind_undecided(self):
        self.assertEqual(check_answer("其他", "5 天")[0], "未定")

    def test_result_has_reason_string(self):
        status, reason = check_answer("預算", "盡快處理")
        self.assertTrue(isinstance(reason, str) and reason)


if __name__ == "__main__":
    unittest.main()
