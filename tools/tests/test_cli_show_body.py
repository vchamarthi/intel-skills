"""`intel-skills show <skill> --body` prints SKILL.md without the provenance header."""

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "bin" / "intel-skills.mjs"


def run(*args):
    return subprocess.run(
        ["node", str(CLI), *args], capture_output=True, text=True, check=False
    )


class ShowBodyTest(unittest.TestCase):
    def test_imported_skill_body_has_no_provenance_header(self):
        result = run("show", "model-can-it-fit", "--body")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith("---\n"), result.stdout[:80])
        self.assertNotIn("upstream:  ", result.stdout)
        self.assertNotIn("pinned:    ", result.stdout)

    def test_flag_may_precede_the_skill_name(self):
        result = run("show", "--body", "dpnp-quickstart")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("name: dpnp-quickstart", result.stdout)

    def test_show_without_flag_keeps_the_provenance_header(self):
        result = run("show", "model-can-it-fit")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("upstream:  ", result.stdout)


if __name__ == "__main__":
    unittest.main()
