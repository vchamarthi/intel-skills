"""`install --target` is validated even when `--dir` overrides the location."""

import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "bin" / "intel-skills.mjs"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["node", str(CLI), *args], capture_output=True, text=True, check=False
    )


def first_skill() -> str:
    return run("list").stdout.splitlines()[0].split("\t")[0]


def test_unknown_target_with_dir_is_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        result = run("install", first_skill(), "--target", "claud-code", "--dir", tmp)
        assert result.returncode == 1
        assert "unknown target: claud-code" in result.stderr
        assert not any(Path(tmp).iterdir())


def test_known_target_with_dir_installs_into_dir():
    with tempfile.TemporaryDirectory() as tmp:
        name = first_skill()
        result = run("install", name, "--target", "agents", "--dir", tmp)
        assert result.returncode == 0, result.stderr
        assert (Path(tmp) / name / "SKILL.md").is_file()


def test_dir_alone_still_installs():
    with tempfile.TemporaryDirectory() as tmp:
        name = first_skill()
        assert run("install", name, "--dir", tmp).returncode == 0
