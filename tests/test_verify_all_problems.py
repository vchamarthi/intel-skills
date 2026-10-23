"""`verify --all-problems` lists every drifted file instead of the first four.

Standard library only, like the rest of the tooling: `python3 -m unittest discover -s tests`.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "bin" / "intel-skills.mjs"


def run(*args):
    return subprocess.run(["node", str(CLI), *args], capture_output=True, text=True, check=False)


class VerifyAllProblems(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.assertEqual(run("install", "linux-perf", "--dir", str(self.root)).returncode, 0)
        self.skill = self.root / "linux-perf"

    def add_strays(self, count):
        for i in range(count):
            (self.skill / f"stray-{i}.txt").write_text("x")

    def test_default_truncates_after_four_problems(self):
        self.add_strays(6)
        result = run("verify", "linux-perf", "--path", str(self.skill))
        self.assertEqual(result.returncode, 1)
        self.assertIn("(+2 more", result.stderr)
        self.assertNotIn("stray-5.txt", result.stderr)

    def test_all_problems_lists_every_file(self):
        self.add_strays(6)
        result = run("verify", "linux-perf", "--path", str(self.skill), "--all-problems")
        self.assertEqual(result.returncode, 1)
        for i in range(6):
            self.assertIn(f"stray-{i}.txt is not part of this skill", result.stderr)
        self.assertNotIn("(+", result.stderr)

    def test_clean_install_still_verifies_with_flag(self):
        result = run("verify", "linux-perf", "--path", str(self.skill), "--all-problems")
        self.assertEqual(result.returncode, 0)
        self.assertTrue(result.stdout.startswith("ok linux-perf"))


if __name__ == "__main__":
    unittest.main()
