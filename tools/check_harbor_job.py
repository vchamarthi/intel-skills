#!/usr/bin/env python3
"""Assert a Harbor job met its floor. Exit 0 pass, 1 fail.

Harbor runs the evaluation and owns the result format; this script only decides
whether a finished job is acceptable, so that "the oracle smoke passed" is a
machine check and not a human reading a table.

Usage:
    python3 tools/check_harbor_job.py harbor-jobs/<job>/result.json \\
        --expected-trials 5 --reward-floor 1.0

Three failures are treated as distinct, because they have different causes:

  missing trial   the job ran fewer trials than expected. Usually a task-name
                  filter that matched nothing — a job that silently evaluated
                  four of five tasks otherwise reports a clean mean.
  errored trial   the harness failed (build, timeout, RewardFileNotFoundError).
                  This is not a low score; there is no score.
  below floor     the trial ran and scored under the floor.

Reads the per-trial result.json files next to the job's, not just the job
summary: the trial's own reward and exception are authoritative, and a headline
mean can hide a single zero.

Stdlib only, no network, no credentials — so it can run in the same job as the
Level 1 gates.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

REWARD_KEY = "reward"


class LoadError(Exception):
    """A job or trial result.json that cannot be read."""


def load(path: Path) -> dict:
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        raise LoadError(f"no such file: {path}") from None
    except json.JSONDecodeError as exc:
        raise LoadError(f"{path} is not valid JSON: {exc}") from None


def collect_trials(job_result: Path) -> list[dict]:
    """Every trial result.json in the job directory, sorted by task name.

    A trial that Harbor never finished may have no result.json at all; those are
    caught by the expected-trials count, not here.
    """
    trials = []
    for candidate in sorted(job_result.parent.glob("*/result.json")):
        trials.append(load(candidate))
    return sorted(trials, key=lambda t: (t.get("task_name") or "", t.get("trial_name") or ""))


def reward_of(trial: dict) -> float | None:
    """The trial's combined reward, or None when the verifier produced none.

    NaN and infinity are treated as no reward: they have no meaningful floor
    comparison and are not representable in standard JSON output.
    """
    rewards = (trial.get("verifier_result") or {}).get("rewards") or {}
    value = rewards.get(REWARD_KEY)
    if isinstance(value, (int, float)) and math.isfinite(value):
        return float(value)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("result", type=Path, help="harbor-jobs/<job>/result.json")
    parser.add_argument(
        "--expected-trials",
        type=int,
        required=True,
        help="how many trials this job must contain; a smaller number is a failure",
    )
    parser.add_argument(
        "--reward-floor",
        type=float,
        default=1.0,
        help="minimum per-trial reward (default 1.0, the oracle's floor)",
    )
    parser.add_argument(
        "--allow-errors",
        action="store_true",
        help="report errored trials without failing; for exploratory runs only",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print one JSON verdict (ok, problems, trials) instead of the text report",
    )
    args = parser.parse_args()
    # In --json mode the text report is dropped; stdout carries only the verdict.
    say = (lambda *a, **k: None) if args.json else print

    try:
        job = load(args.result)
        trials = collect_trials(args.result)
    except LoadError as exc:
        if args.json:
            print(json.dumps({"ok": False, "problems": [str(exc)], "trials": []}, indent=2))
            return 1
        sys.exit(f"FAIL {exc}")
    stats = job.get("stats") or {}

    problems: list[str] = []
    n_reported = job.get("n_total_trials")
    if n_reported != args.expected_trials:
        problems.append(
            f"expected {args.expected_trials} trials, job reports {n_reported}. "
            "Check that --include-task-name matched every task you meant."
        )
    if len(trials) != args.expected_trials:
        problems.append(
            f"expected {args.expected_trials} trial directories, found {len(trials)}"
        )

    say(f"job     {args.result.parent.name}")
    say(
        f"trials  {stats.get('n_completed_trials')} completed, "
        f"{stats.get('n_errored_trials')} errored, "
        f"{stats.get('n_cancelled_trials')} cancelled, "
        f"{stats.get('n_retries')} retries"
    )
    say(f"floor   reward >= {args.reward_floor}")
    say()

    rows: list[dict] = []
    for trial in trials:
        name = trial.get("task_name") or trial.get("trial_name") or "<unnamed>"
        exception = trial.get("exception_info")
        reward = reward_of(trial)
        rows.append(
            {
                "task": name,
                "reward": reward,
                "error": (exception.get("exception_type") or "unknown") if exception else None,
            }
        )

        if exception:
            kind = exception.get("exception_type") or "unknown"
            line = f"ERROR {name}: {kind}"
            say(line)
            if not args.allow_errors:
                problems.append(f"{name} errored: {kind}")
            continue

        if reward is None:
            say(f"ERROR {name}: verifier reported no '{REWARD_KEY}'")
            problems.append(
                f"{name} produced no reward. The verifier must write "
                f"/logs/verifier/reward.txt or reward.json."
            )
            continue

        verdict = "ok   " if reward >= args.reward_floor else "BELOW"
        say(f"{verdict} {name}: {reward:.3f}")
        if reward < args.reward_floor:
            problems.append(f"{name} scored {reward:.3f} < {args.reward_floor}")

        # A rubric verifier emits components alongside the combined reward. Name
        # them so a component regression is visible even when the total passes.
        extra = {
            key: value
            for key, value in ((trial.get("verifier_result") or {}).get("rewards") or {}).items()
            if key != REWARD_KEY
        }
        if extra:
            parts = ", ".join(f"{key}={value}" for key, value in sorted(extra.items()))
            say(f"        components: {parts}")

    say()
    if args.json:
        print(json.dumps({"ok": not problems, "problems": problems, "trials": rows}, indent=2))
        return 1 if problems else 0
    if problems:
        say(f"FAIL {len(problems)} problem(s):")
        for problem in problems:
            say(f"  - {problem}")
        return 1

    say(f"OK {len(trials)} trial(s) at or above {args.reward_floor}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
