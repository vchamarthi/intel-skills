"""`--help` after any installer subcommand prints usage and exits 0."""

import subprocess
import sys
from pathlib import Path

import pytest

CLI = Path(__file__).resolve().parents[2] / "bin" / "intel-skills.mjs"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["node", str(CLI), *args], capture_output=True, text=True, check=False
    )


@pytest.mark.parametrize(
    "args",
    [
        ("install", "--help"),
        ("install", "-h"),
        ("verify", "--help"),
        ("show", "--help"),
        ("list", "--help"),
    ],
)
def test_subcommand_help_prints_usage(args: tuple[str, ...]) -> None:
    result = run(*args)
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("Usage:")
    assert "invalid skill name" not in result.stderr


def test_list_still_lists_without_help() -> None:
    result = run("list")
    assert result.returncode == 0
    assert "Usage:" not in result.stdout


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
