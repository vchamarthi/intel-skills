"""`intel-skills verify --all --path <dir>` checks every catalog skill under one directory."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "bin" / "intel-skills.mjs"


def run(*args):
    return subprocess.run(
        ["node", str(CLI), *args], capture_output=True, text=True, check=False
    )


def test_verify_all_accepts_a_full_install(tmp_path):
    assert run("install", "--all", "--dir", str(tmp_path)).returncode == 0
    result = run("verify", "--all", "--path", str(tmp_path))
    assert result.returncode == 0, result.stderr
    assert "verified under" in result.stdout


def test_verify_all_names_the_altered_and_the_missing_skill(tmp_path):
    assert run("install", "--all", "--dir", str(tmp_path)).returncode == 0
    names = sorted(p.name for p in (ROOT / "skills").iterdir() if (p / "SKILL.md").is_file())
    (tmp_path / names[0] / "SKILL.md").write_text("altered\n", encoding="utf-8")
    for child in sorted((tmp_path / names[1]).rglob("*"), reverse=True):
        child.unlink() if child.is_file() else child.rmdir()
    (tmp_path / names[1]).rmdir()

    result = run("verify", "--all", "--path", str(tmp_path))
    assert result.returncode == 1
    assert f"error: {names[0]}:" in result.stderr
    assert f"error: {names[1]}:" in result.stderr
    assert f"{len(names) - 2}/{len(names)} verified" in result.stdout


def test_verify_all_needs_a_path():
    assert run("verify", "--all").returncode == 1


def test_verify_all_rejects_a_missing_directory(tmp_path):
    result = run("verify", "--all", "--path", str(tmp_path / "absent"))
    assert result.returncode == 1
    assert "no such directory" in result.stderr
