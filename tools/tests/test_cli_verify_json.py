"""`intel-skills verify --json` reports the comparison as one JSON object."""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "bin" / "intel-skills.mjs"
SKILL = "linux-perf"


def run(*args):
    return subprocess.run(["node", str(CLI), *args], capture_output=True, text=True, check=False)


def install(tmp_path):
    assert run("install", SKILL, "--dir", str(tmp_path)).returncode == 0
    return tmp_path / SKILL


def test_matching_install_reports_ok(tmp_path):
    installed = install(tmp_path)
    result = run("verify", SKILL, "--path", str(installed), "--json")
    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["skill"] == SKILL
    assert report["ok"] is True
    assert report["problems"] == []
    assert report["files"] > 0


def test_altered_install_lists_every_problem_and_exits_nonzero(tmp_path):
    installed = install(tmp_path)
    with (installed / "SKILL.md").open("a") as handle:
        handle.write("\nextra\n")
    for index in range(5):
        (installed / f"stray-{index}.md").write_text("x")
    result = run("verify", SKILL, "--path", str(installed), "--json")
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["ok"] is False
    assert "SKILL.md differs from the catalog" in report["problems"]
    assert len(report["problems"]) == 6


def test_text_output_is_unchanged_without_the_flag(tmp_path):
    installed = install(tmp_path)
    result = run("verify", SKILL, "--path", str(installed))
    assert result.returncode == 0
    assert result.stdout.startswith(f"ok {SKILL} (")
