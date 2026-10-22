"""`install` and `verify` take their flags before or after the skill name."""

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


@pytest.mark.parametrize("flags_first", [False, True])
def test_install_then_verify_accepts_either_flag_order(tmp_path, flags_first):
    target = tmp_path / "skills"
    if flags_first:
        install = run("install", "--force", "--dir", str(target), SKILL)
    else:
        install = run("install", SKILL, "--dir", str(target), "--force")
    assert install.returncode == 0, install.stderr
    assert (target / SKILL / "SKILL.md").is_file()

    path = str(target / SKILL)
    verify = run("verify", "--path", path, SKILL) if flags_first else run("verify", SKILL, "--path", path)
    assert verify.returncode == 0, verify.stderr
    assert verify.stdout.startswith(f"ok {SKILL}")


def test_install_with_only_flags_prints_usage(tmp_path):
    result = run("install", "--dir", str(tmp_path))
    assert result.returncode == 1
    assert "Usage:" in result.stdout
