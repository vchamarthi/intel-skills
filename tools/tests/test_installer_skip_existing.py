"""`install --skip-existing` leaves an already-installed skill alone instead of failing."""

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "bin" / "intel-skills.mjs"
SKILL = "linux-perf"


def run(*args):
    return subprocess.run(["node", str(CLI), *args], capture_output=True, text=True, check=False)


class SkipExistingTest(unittest.TestCase):
    def test_rerun_install_all_skips_what_is_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run("install", SKILL, "--dir", tmp).returncode, 0)
            result = run("install", "--all", "--dir", tmp, "--skip-existing")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"skipped {SKILL}", result.stdout)
            total = len(run("list").stdout.splitlines())
            self.assertIn(f"{total - 1}/{total} installed to", result.stdout)
            self.assertIn("(1 skipped)", result.stdout)
            self.assertTrue((Path(tmp) / "linux-perf" / "SKILL.md").exists())
            installed = [p for p in Path(tmp).iterdir() if p.is_dir()]
            self.assertEqual(len(installed), total)

    def test_single_skill_is_skipped_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run("install", SKILL, "--dir", tmp).returncode, 0)
            marker = Path(tmp) / SKILL / "SKILL.md"
            marker.write_text("local edit")
            result = run("install", SKILL, "--dir", tmp, "--skip-existing")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(marker.read_text(), "local edit")

    def test_without_the_flag_an_existing_skill_still_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run("install", SKILL, "--dir", tmp).returncode, 0)
            self.assertNotEqual(run("install", SKILL, "--dir", tmp).returncode, 0)

    def test_force_and_skip_existing_are_rejected_together(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run("install", SKILL, "--dir", tmp).returncode, 0)
            marker = Path(tmp) / SKILL / "SKILL.md"
            marker.write_text("local edit")
            result = run("install", SKILL, "--dir", tmp, "--force", "--skip-existing")
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(marker.read_text(), "local edit")


if __name__ == "__main__":
    unittest.main()
