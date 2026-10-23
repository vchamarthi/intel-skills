"""`intel-skills path <skill>` prints the skill's directory in the checkout."""

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "bin" / "intel-skills.mjs"


def run(*args):
    return subprocess.run(
        ["node", str(CLI), *args], capture_output=True, text=True, check=False
    )


class PathTest(unittest.TestCase):
    def test_prints_directory_holding_skill_md(self):
        result = run("path", "dpnp-quickstart")
        self.assertEqual(result.returncode, 0, result.stderr)
        skill_dir = Path(result.stdout.strip())
        self.assertEqual(skill_dir, ROOT / "skills" / "dpnp-quickstart")
        self.assertTrue((skill_dir / "SKILL.md").is_file())

    def test_unknown_skill_fails(self):
        result = run("path", "no-such-skill")
        self.assertEqual(result.returncode, 1)
        self.assertIn("skill not found: no-such-skill", result.stderr)

    def test_missing_name_prints_usage(self):
        result = run("path")
        self.assertEqual(result.returncode, 1)
        self.assertIn("intel-skills path <skill>", result.stdout)


if __name__ == "__main__":
    unittest.main()
