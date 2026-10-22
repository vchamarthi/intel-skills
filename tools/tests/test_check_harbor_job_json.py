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


def strict_loads(text: str):
    def reject(token: str):
        raise ValueError(f"non-standard JSON token {token}")

    return json.loads(text, parse_constant=reject)


def test_json_missing_job_is_structured_failure(tmp_path):
    proc = run(tmp_path / "missing.json", "--json")
    assert proc.returncode == 1
    data = strict_loads(proc.stdout)
    assert data["ok"] is False
    assert any("no such file" in p for p in data["problems"])
    assert data["trials"] == []


def test_json_malformed_job_is_structured_failure(tmp_path):
    result = make_job(tmp_path, {"a": 1.0, "b": 1.0})
    result.write_text("{not json", encoding="utf-8")
    proc = run(result, "--json")
    assert proc.returncode == 1
    data = strict_loads(proc.stdout)
    assert data["ok"] is False
    assert any("not valid JSON" in p for p in data["problems"])


def test_json_malformed_trial_is_structured_failure(tmp_path):
    result = make_job(tmp_path, {"a": 1.0, "b": 1.0})
    (result.parent / "b__abc" / "result.json").write_text("{", encoding="utf-8")
    proc = run(result, "--json")
    assert proc.returncode == 1
    assert strict_loads(proc.stdout)["ok"] is False


def assert_structured_failure(proc, fragment: str):
    assert proc.returncode == 1
    assert "Traceback" not in proc.stderr
    data = strict_loads(proc.stdout)
    assert data["ok"] is False
    assert any(fragment in p for p in data["problems"])
    return data


def test_json_non_object_job_is_structured_failure(tmp_path):
    for index, body in enumerate(("[]", "null", "3")):
        root = tmp_path / f"job-{index}"
        root.mkdir()
        result = make_job(root, {"a": 1.0, "b": 1.0})
        result.write_text(body, encoding="utf-8")
        assert_structured_failure(run(result, "--json"), "not a JSON object")


def test_json_non_object_trial_is_structured_failure(tmp_path):
    result = make_job(tmp_path, {"a": 1.0, "b": 1.0})
    (result.parent / "b__abc" / "result.json").write_text("[1]", encoding="utf-8")
    assert_structured_failure(run(result, "--json"), "not a JSON object")


def test_json_directory_as_job_file_is_structured_failure(tmp_path):
    result = tmp_path / "result.json"
    result.mkdir()
    assert_structured_failure(run(result, "--json"), "cannot read")


def test_json_directory_as_trial_file_is_structured_failure(tmp_path):
    result = make_job(tmp_path, {"a": 1.0, "b": 1.0})
    trial_file = result.parent / "b__abc" / "result.json"
    trial_file.unlink()
    trial_file.mkdir()
    assert_structured_failure(run(result, "--json"), "cannot read")


def test_json_invalid_utf8_is_structured_failure(tmp_path):
    result = make_job(tmp_path, {"a": 1.0, "b": 1.0})
    result.write_bytes(b'{"n_total_trials": "\xff\xfe"}')
    assert_structured_failure(run(result, "--json"), "cannot read")


def test_text_mode_non_object_job_fails_without_traceback(tmp_path):
    result = make_job(tmp_path, {"a": 1.0, "b": 1.0})
    result.write_text("[]", encoding="utf-8")
    proc = run(result)
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert "FAIL" in proc.stderr and "Traceback" not in proc.stderr


def test_json_wrong_shaped_job_stats_does_not_crash(tmp_path):
    for index, stats in enumerate(("[]", '"x"', "7", "null")):
        root = tmp_path / f"stats-{index}"
        root.mkdir()
        result = make_job(root, {"a": 1.0, "b": 1.0})
        result.write_text(
            '{"n_total_trials": 2, "stats": %s}' % stats, encoding="utf-8"
        )
        proc = run(result, "--json")
        assert proc.returncode == 0, proc.stderr
        assert strict_loads(proc.stdout)["ok"] is True


def test_json_wrong_shaped_trial_fields_do_not_crash(tmp_path):
    result = make_job(tmp_path, {"a": 1.0, "b": 1.0})
    (result.parent / "a__abc" / "result.json").write_text(
        json.dumps({"task_name": 5, "trial_name": ["x"], "verifier_result": []}),
        encoding="utf-8",
    )
    (result.parent / "b__abc" / "result.json").write_text(
        json.dumps({"task_name": "b", "verifier_result": {"rewards": [1.0]}}),
        encoding="utf-8",
    )
    proc = run(result, "--json")
    assert proc.returncode == 1
    assert "Traceback" not in proc.stderr
    data = strict_loads(proc.stdout)
    assert [t["reward"] for t in data["trials"]] == [None, None]
    assert len(data["problems"]) == 2


def test_json_wrong_shaped_exception_info_is_an_error(tmp_path):
    for index, info in enumerate(('"boom"', "[1]", '{"exception_type": 5}')):
        root = tmp_path / f"exc-{index}"
        root.mkdir()
        result = make_job(root, {"a": 1.0, "b": 1.0})
        (result.parent / "b__abc" / "result.json").write_text(
            '{"task_name": "b", "exception_info": %s}' % info, encoding="utf-8"
        )
        proc = run(result, "--json")
        assert proc.returncode == 1, info
        data = strict_loads(proc.stdout)
        assert data["trials"][1]["error"] == "unknown"
        assert any("b errored: unknown" in p for p in data["problems"])


def test_text_mode_failure_message_unchanged(tmp_path):
    proc = run(tmp_path / "missing.json")
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert "FAIL no such file" in proc.stderr


def test_json_non_finite_reward_is_null_and_strict(tmp_path):
    result = make_job(tmp_path, {"a": 1.0, "b": 1.0})
    # json.dumps writes NaN / Infinity, which Python's json module reads back.
    (result.parent / "b__abc" / "result.json").write_text(
        '{"task_name": "b", "verifier_result": {"rewards": {"reward": NaN}}}',
        encoding="utf-8",
    )
    (result.parent / "a__abc" / "result.json").write_text(
        '{"task_name": "a", "verifier_result": {"rewards": {"reward": Infinity}}}',
        encoding="utf-8",
    )
    proc = run(result, "--json")
    assert proc.returncode == 1
    data = strict_loads(proc.stdout)
    assert [t["reward"] for t in data["trials"]] == [None, None]
    assert data["ok"] is False


def test_allow_errors_tolerates_errored_trial(tmp_path):
    # --allow-errors is for exploratory runs: an errored trial is reported, not failed.
    result = make_job(tmp_path, {"a": 1.0, "b": 1.0})
    (result.parent / "b__abc" / "result.json").write_text(
        json.dumps({"task_name": "b", "exception_info": {"exception_type": "Timeout"}}),
        encoding="utf-8",
    )
    proc = run(result, "--json", "--allow-errors")
    assert proc.returncode == 0
    data = strict_loads(proc.stdout)
    assert data["trials"][1]["error"] == "Timeout"


def test_default_output_unchanged(tmp_path):
    proc = run(make_job(tmp_path, {"a": 1.0, "b": 1.0}))
    assert proc.returncode == 0
    assert proc.stdout.rstrip().endswith("OK 2 trial(s) at or above 1.0")
