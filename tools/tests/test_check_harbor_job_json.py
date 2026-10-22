"""check_harbor_job.py --json prints one machine-readable verdict."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "check_harbor_job.py"


def make_job(root: Path, rewards: dict[str, float | None]) -> Path:
    job = root / "job"
    job.mkdir()
    (job / "result.json").write_text(
        json.dumps({"n_total_trials": len(rewards), "stats": {}}), encoding="utf-8"
    )
    for name, reward in rewards.items():
        trial = job / f"{name}__abc"
        trial.mkdir()
        body = {"task_name": name, "trial_name": f"{name}__abc"}
        if reward is not None:
            body["verifier_result"] = {"rewards": {"reward": reward}}
        (trial / "result.json").write_text(json.dumps(body), encoding="utf-8")
    return job / "result.json"


def run(result: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOL), str(result), "--expected-trials", "2", *extra],
        capture_output=True,
        text=True,
    )


def test_json_pass(tmp_path):
    proc = run(make_job(tmp_path, {"a": 1.0, "b": 1.0}), "--json")
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["ok"] is True
    assert data["problems"] == []
    assert [t["task"] for t in data["trials"]] == ["a", "b"]
    assert data["trials"][0]["reward"] == 1.0


def test_json_fail_lists_problem(tmp_path):
    proc = run(make_job(tmp_path, {"a": 1.0, "b": 0.5}), "--json")
    assert proc.returncode == 1
    data = json.loads(proc.stdout)
    assert data["ok"] is False
    assert any("b scored" in p for p in data["problems"])


def test_json_missing_reward_is_null(tmp_path):
    proc = run(make_job(tmp_path, {"a": 1.0, "b": None}), "--json")
    assert proc.returncode == 1
    data = json.loads(proc.stdout)
    assert data["trials"][1]["reward"] is None


def test_default_output_unchanged(tmp_path):
    proc = run(make_job(tmp_path, {"a": 1.0, "b": 1.0}))
    assert proc.returncode == 0
    assert proc.stdout.rstrip().endswith("OK 2 trial(s) at or above 1.0")
