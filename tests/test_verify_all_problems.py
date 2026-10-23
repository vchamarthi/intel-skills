"""`verify --all-problems` lists every drifted file instead of the first four."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "bin" / "intel-skills.mjs"


def run(*args):
    return subprocess.run(["node", str(CLI), *args], capture_output=True, text=True, check=False)


def tampered_install(tmp_path, extra=6):
    assert run("install", "linux-perf", "--dir", str(tmp_path)).returncode == 0
    skill = tmp_path / "linux-perf"
    for i in range(extra):
        (skill / f"stray-{i}.txt").write_text("x")
    return skill


def test_default_truncates_after_four_problems(tmp_path):
    skill = tampered_install(tmp_path)
    result = run("verify", "linux-perf", "--path", str(skill))
    assert result.returncode == 1
    assert "(+2 more" in result.stderr
    assert "stray-5.txt" not in result.stderr


def test_all_problems_lists_every_file(tmp_path):
    skill = tampered_install(tmp_path)
    result = run("verify", "linux-perf", "--path", str(skill), "--all-problems")
    assert result.returncode == 1
    for i in range(6):
        assert f"stray-{i}.txt is not part of this skill" in result.stderr
    assert "more" not in result.stderr


def test_clean_install_still_verifies_with_flag(tmp_path):
    assert run("install", "linux-perf", "--dir", str(tmp_path)).returncode == 0
    result = run("verify", "linux-perf", "--path", str(tmp_path / "linux-perf"), "--all-problems")
    assert result.returncode == 0
    assert result.stdout.startswith("ok linux-perf")
