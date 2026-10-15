import unittest
from scripts.score_ux import score, InvalidUxData


def attempts(ok_in_first: int = 17, ok_in_second: int = 18, participants: int = 5):
    rows = []
    for rnd, count in ((1, ok_in_first), (2, ok_in_second)):
        for p in range(participants):
            for t in range(4):
                idx = p * 4 + t
                rows.append({
                    "round": str(rnd),
                    "participant_id": f"anon-{p+1}",
                    "task_id": f"T{t+1:02d}",
                    "valid_attempt": "1", "success": "1" if idx < count else "0",
                })
    return rows


class UxScoreTests(unittest.TestCase):
    def test_real_math_17_of_20_meets_85_percent(self):
        result = score(attempts())
        self.assertEqual(result["rounds"]["1"]["completion_rate_percent"], 85)
        self.assertTrue(result["both_rounds_pass"])

    def test_16_of_20_fails(self):
        result = score(attempts(ok_in_first=16))
        self.assertEqual(result["rounds"]["1"]["completion_rate_percent"], 80)
        self.assertFalse(result["both_rounds_pass"])

    def test_four_participants_never_counts_as_complete(self):
        result = score(attempts(participants=4))
        self.assertFalse(result["ready_for_claim"])
        self.assertFalse(result["rounds"]["2"]["passed"])

    def test_missing_round_cannot_be_claimed(self):
        result = score([row for row in attempts() if row["round"] == "1"])
        self.assertFalse(result["ready_for_claim"])

    def test_disallows_duplicate_attempt(self):
        rows = attempts()
        with self.assertRaisesRegex(InvalidUxData, "Duplicate"):
            score(rows + [rows[0]])

    def test_exclusion_requires_documented_reason(self):
        rows = attempts()
        rows[0] = {**rows[0], "valid_attempt": "0", "success": "0"}
        with self.assertRaisesRegex(InvalidUxData, "technical reason"):
            score(rows)

    def test_incomplete_started_task_is_failed_not_excluded(self):
        rows = attempts(ok_in_first=17)
        self.assertEqual(score(rows)["rounds"]["1"]["attempts"], 20)


if __name__ == "__main__":
    unittest.main()
