"""`intel-skills show <skill> --json` prints one machine-readable object.

Standard library only, like the rest of the local gate: `python3 -m unittest discover tests`.
"""

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "bin" / "intel-skills.mjs"


def run(*args):
    return subprocess.run(["node", str(CLI), *args], capture_output=True, text=True, cwd=ROOT)


class ShowJson(unittest.TestCase):
    def test_describes_the_skill(self):
        result = run("show", "linux-perf", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["name"], "linux-perf")
        self.assertTrue(data["description"])
        self.assertIn("SKILL.md", data["files"])
        self.assertEqual(data["files"], sorted(data["files"]))

    def test_flag_may_come_first(self):
        result = run("show", "--json", "linux-perf")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["name"], "linux-perf")

    def test_rejects_unknown_options_and_extra_names(self):
        self.assertEqual(run("show", "linux-perf", "--jsno").returncode, 1)
        self.assertEqual(run("show", "linux-perf", "dpnp-quickstart").returncode, 1)
        self.assertEqual(run("show", "--json").returncode, 1)

    def test_plain_show_still_prints_the_skill_body(self):
        result = run("show", "linux-perf")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("\nname: linux-perf\n", result.stdout)
        self.assertFalse(result.stdout.lstrip().startswith("{"))


if __name__ == "__main__":
    unittest.main()
