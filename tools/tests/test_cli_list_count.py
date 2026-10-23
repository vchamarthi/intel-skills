"""`intel-skills list --count` prints how many skills the catalog holds."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "bin" / "intel-skills.mjs"


def run(*args):
    return subprocess.run(["node", str(CLI), *args], capture_output=True, text=True, check=False)


def test_count_matches_listed_rows():
    rows = run("list").stdout.splitlines()
    result = run("list", "--count")
    assert result.returncode == 0
    assert result.stdout.strip() == str(len(rows))
