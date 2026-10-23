"""`intel-skills list --from <repo>` shows only the skills imported from that repository."""

import subprocess
from pathlib import Path

CLI = Path(__file__).resolve().parents[1] / "bin" / "intel-skills.mjs"


def run(*args):
    return subprocess.run(["node", str(CLI), *args], capture_output=True, text=True, check=False)


def test_from_keeps_only_that_upstream():
    result = run("list", "--from", "intel-performance-skills")
    assert result.returncode == 0
    names = [line.split("\t")[0] for line in result.stdout.splitlines()]
    assert names == ["linux-perf", "performance-patterns", "phoronix-test-suite"]
    assert all("\timported\tintel-performance-skills@" in line for line in result.stdout.splitlines())


def test_from_unknown_repo_fails():
    result = run("list", "--from", "no-such-repo")
    assert result.returncode == 1
    assert "no skills imported from no-such-repo" in result.stderr
    assert result.stdout == ""


def test_from_requires_a_value():
    result = run("list", "--from")
    assert result.returncode == 1
    assert "--from requires a value" in result.stderr


def test_plain_list_is_unchanged():
    result = run("list")
    assert result.returncode == 0
    assert any("\town\t" in line for line in result.stdout.splitlines())
    assert "gpu-ai-skills@" in result.stdout
