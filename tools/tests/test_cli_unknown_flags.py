"""`install` and `verify` refuse an option they do not know instead of ignoring it."""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "bin" / "intel-skills.mjs"
SKILL = sorted(p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md"))[0]

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def run(*args):
    return subprocess.run(["node", str(CLI), *args], capture_output=True, text=True, check=False)


def test_install_rejects_misspelled_flag_and_writes_nothing(tmp_path):
    result = run("install", SKILL, "--dir", str(tmp_path / "skills"), "--forse")
    assert result.returncode == 1
    assert "unknown option: --forse" in result.stderr
    assert not (tmp_path / "skills").exists()


def test_install_rejects_all_combined_with_a_skill_name(tmp_path):
    result = run("install", SKILL, "--all", "--dir", str(tmp_path / "skills"))
    assert result.returncode == 1
    assert "--all" in result.stderr
    assert not (tmp_path / "skills").exists()


def test_verify_rejects_unknown_flag(tmp_path):
    target = tmp_path / "skills"
    assert run("install", SKILL, "--dir", str(target)).returncode == 0
    result = run("verify", SKILL, "--path", str(target / SKILL), "--bogus")
    assert result.returncode == 1
    assert "unknown option: --bogus" in result.stderr


def test_known_flags_still_work(tmp_path):
    target = tmp_path / "skills"
    assert run("install", SKILL, "--dir", str(target), "--force").returncode == 0
    assert run("install", SKILL, "--dir", str(target), "--force").returncode == 0
    verified = run("verify", SKILL, "--path", str(target / SKILL))
    assert verified.returncode == 0, verified.stderr
