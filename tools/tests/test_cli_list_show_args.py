"""`list` and `show` refuse arguments they do not understand instead of ignoring them."""

import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "bin" / "intel-skills.mjs"
SKILL = sorted(p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md"))[0]


def run(*args):
    return subprocess.run(["node", str(CLI), *args], capture_output=True, text=True, check=False)


@unittest.skipIf(shutil.which("node") is None, "node not installed")
class ListShowArgsTests(unittest.TestCase):
    def test_list_with_an_unknown_flag_is_an_error(self):
        result = run("list", "--json")
        self.assertEqual(result.returncode, 1)
        self.assertIn("list takes no arguments (got --json)", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_list_alone_prints_the_catalog(self):
        result = run("list")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(SKILL, result.stdout)

    def test_show_with_an_extra_argument_is_an_error(self):
        result = run("show", SKILL, "other-skill")
        self.assertEqual(result.returncode, 1)
        self.assertIn("extra argument other-skill", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_show_with_one_name_still_prints_the_skill(self):
        result = run("show", SKILL)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"name: {SKILL}", result.stdout)


if __name__ == "__main__":
    unittest.main()
