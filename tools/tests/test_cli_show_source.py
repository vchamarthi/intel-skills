"""`intel-skills show <skill> --source` prints provenance only, without the SKILL.md body."""

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "bin" / "intel-skills.mjs"


def run(*args):
    return subprocess.run(
        ["node", str(CLI), *args], capture_output=True, text=True, check=False
    )


class ShowSourceTest(unittest.TestCase):
    def test_imported_skill_prints_only_provenance(self):
        result = run("show", "model-can-it-fit", "--source")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("upstream:  https://github.com/intel/gpu-ai-skills/tree/", result.stdout)
        self.assertIn("pinned:    ", result.stdout)
        self.assertIn("license:   ", result.stdout)
        self.assertNotIn("name: model-can-it-fit", result.stdout)

    def test_own_skill_says_where_it_is_maintained(self):
        result = run("show", "--source", "dpnp-quickstart")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "maintained in this repository")

    def test_show_without_flag_still_prints_the_body(self):
        result = run("show", "linux-perf")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("name: linux-perf", result.stdout)


if __name__ == "__main__":
    unittest.main()
