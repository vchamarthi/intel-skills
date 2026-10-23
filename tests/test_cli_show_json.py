"""`intel-skills show <skill> --json` prints one machine-readable object."""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "bin" / "intel-skills.mjs"


def run(*args):
    return subprocess.run(["node", str(CLI), *args], capture_output=True, text=True, cwd=ROOT)


def test_show_json_describes_the_skill():
    result = run("show", "linux-perf", "--json")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["name"] == "linux-perf"
    assert data["description"]
    assert "SKILL.md" in data["files"]
    assert data["files"] == sorted(data["files"])


def test_show_json_flag_may_come_first():
    result = run("show", "--json", "linux-perf")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["name"] == "linux-perf"


def test_show_without_json_still_prints_the_skill_body():
    result = run("show", "linux-perf")
    assert result.returncode == 0, result.stderr
    assert "\nname: linux-perf\n" in result.stdout
    assert not result.stdout.lstrip().startswith("{")
