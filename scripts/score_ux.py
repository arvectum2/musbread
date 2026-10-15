#!/usr/bin/env python3
"""Evaluate REAL anonymized UX attempts; no hardcoded success counts.

A round is not considered eligible until it has >= 5 real participants.
Each started, valid attempt is counted, including failed or incomplete tasks.
"""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


class InvalidUxData(ValueError):
    pass


def score(rows: list[dict[str, str]], threshold: float = 85.0, min_participants: int = 5) -> dict:
    if not 0 <= threshold <= 100 or min_participants < 1:
        raise InvalidUxData("Invalid threshold or min participants")

    results = {}
    unique = set()
    for row in rows:
        rnd = str(row.get("round", "")).strip()
        pid = str(row.get("participant_id", "")).strip()
        task = str(row.get("task_id", "")).strip()
        attempted = str(row.get("valid_attempt", "")).strip()
        success = str(row.get("success", "")).strip()
        reason = str(row.get("invalidation_reason", "")).strip()
        if rnd not in {"1", "2"} or not pid or not task:
            raise InvalidUxData("Round must be 1/2; anonymized participant_id and task_id required")
        if attempted not in {"0", "1"} or success not in {"0", "1"}:
            raise InvalidUxData("valid_attempt and success must be 0/1")
        if attempted == "0" and not reason:
            raise InvalidUxData("Invalidated attempts require a documented technical reason")
        if attempted == "0" and success == "1":
            raise InvalidUxData("Excluded attempt cannot be marked successful")
        key = (rnd, pid, task)
        if key in unique:
            raise InvalidUxData("Duplicate round/participant/task attempt: " + "/".join(key))
        unique.add(key)

        record = results.setdefault(rnd, {"participants": set(), "attempts": 0,
                                         "successes": 0, "invalidated": 0})
        if attempted == "0":
            record["invalidated"] += 1
            continue
        record["participants"].add(pid)
        record["attempts"] += 1
        record["successes"] += int(success)

    summary = {}
    for rnd in ("1", "2"):
        result = results.get(rnd, {"participants": set(), "attempts": 0,
                                   "successes": 0, "invalidated": 0})
        n = result["attempts"]
        people = len(result["participants"])
        completion = round(100.0 * result["successes"] / n, 2) if n else None
        ready = people >= min_participants and n >= people
        summary[rnd] = {
            "participants": people,
            "attempts": n,
            "successes": result["successes"],
            "invalidated": result["invalidated"],
            "completion_rate_percent": completion,
            "threshold_percent": threshold,
            "eligible": ready,
            "passed": bool(ready and completion is not None and completion >= threshold),
        }
    return {"rounds": summary, "ready_for_claim": all(x["eligible"] for x in summary.values()),
            "both_rounds_pass": all(x["passed"] for x in summary.values())}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--threshold", type=float, default=85)
    parser.add_argument("--min-participants", type=int, default=5)
    args = parser.parse_args()
    with args.csv_path.open("r", newline="", encoding="utf-8-sig") as stream:
        summary = score(list(csv.DictReader(stream)), args.threshold, args.min_participants)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    # 2: insufficient sample, 1: sample adequate but threshold not met.
    if not summary["ready_for_claim"]:
        return 2
    return 0 if summary["both_rounds_pass"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (InvalidUxData, OSError, csv.Error) as error:
        print("Invalid UX measurements:", error)
        raise SystemExit(3) from error
