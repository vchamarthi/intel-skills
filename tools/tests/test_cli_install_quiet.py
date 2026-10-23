"""`intel-skills install --quiet` drops the per-skill lines and keeps the summary."""

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "bin" / "intel-skills.mjs"


def run(*args):
    return subprocess.run(["node", str(CLI), *args], capture_output=True, text=True, check=False)


class InstallQuietTest(unittest.TestCase):
    def test_single_install_prints_nothing(self):
        name = sorted(p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md"))[0]
        with tempfile.TemporaryDirectory() as tmp:
            result = run("install", name, "--dir", tmp, "--quiet")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertTrue((Path(tmp) / name / "SKILL.md").is_file())

    def test_all_keeps_only_the_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run("install", "--all", "--dir", tmp, "-q")
            self.assertEqual(result.returncode, 0, result.stderr)
            lines = result.stdout.splitlines()
            self.assertEqual(len(lines), 1)
            self.assertIn("installed to", lines[0])

    def test_default_still_reports_each_skill(self):
        name = sorted(p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md"))[0]
        with tempfile.TemporaryDirectory() as tmp:
            result = run("install", name, "--dir", tmp)
            self.assertTrue(result.stdout.startswith(f"installed {name} ->"))


if __name__ == "__main__":
    unittest.main()
