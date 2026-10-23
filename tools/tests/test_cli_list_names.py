"""`intel-skills list --names` prints bare skill names, one per line."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "bin" / "intel-skills.mjs"


def run(*args):
    return subprocess.run(
        ["node", str(CLI), *args], capture_output=True, text=True, check=False
    )


def test_names_matches_first_column_of_list():
    table = run("list")
    names = run("list", "--names")
    assert table.returncode == 0 and names.returncode == 0
    expected = [line.split("\t")[0] for line in table.stdout.splitlines()]
    assert names.stdout.splitlines() == expected
    assert "\t" not in names.stdout
    assert len(expected) > 0
