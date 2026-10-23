"""`intel-skills installed` lists the skills present in an install directory."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "bin" / "intel-skills.mjs"


def run(*args):
    return subprocess.run(["node", str(CLI), *args], capture_output=True, text=True, check=False)


@unittest.skipIf(shutil.which("node") is None, "node not installed")
class InstalledTests(unittest.TestCase):
    def test_lists_installed_skills_and_flags_foreign_ones(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = sorted(p.name for p in (ROOT / "skills").iterdir() if (p / "SKILL.md").exists())[0]
            self.assertEqual(run("install", first, "--dir", tmp).returncode, 0)
            foreign = Path(tmp) / "someone-elses-skill"
            foreign.mkdir()
            (foreign / "SKILL.md").write_text("---\nname: x\n---\n", encoding="utf-8")
            (Path(tmp) / "not-a-skill").mkdir()
            result = run("installed", "--dir", tmp)
            self.assertEqual(result.returncode, 0, result.stderr)
            lines = result.stdout.splitlines()
            self.assertEqual(lines[0], first)
            self.assertIn("someone-elses-skill\t(not in this catalog)", lines)
            self.assertNotIn("not-a-skill", result.stdout)
            self.assertTrue(lines[-1].startswith("2 skill(s) in "))

    def test_missing_directory_reports_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run("installed", "--dir", str(Path(tmp) / "absent"))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(result.stdout.startswith("0 skill(s) in "))

    def test_requires_target_or_dir(self):
        self.assertEqual(run("installed").returncode, 1)


if __name__ == "__main__":
    unittest.main()
