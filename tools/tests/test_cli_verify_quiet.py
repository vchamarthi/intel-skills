"""`intel-skills verify <skill> --path <dir> --quiet` reports through the exit code only."""

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "bin" / "intel-skills.mjs"


def run(*args):
    return subprocess.run(
        ["node", str(CLI), *args], capture_output=True, text=True, check=False
    )


class VerifyQuietTest(unittest.TestCase):
    def install(self, root):
        result = run("install", "linux-perf", "--dir", root)
        self.assertEqual(result.returncode, 0, result.stderr)
        return Path(root) / "linux-perf"

    def test_matching_install_prints_nothing(self):
        with tempfile.TemporaryDirectory() as root:
            installed = self.install(root)
            result = run("verify", "linux-perf", "--path", str(installed), "--quiet")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")

    def test_without_flag_still_prints_ok(self):
        with tempfile.TemporaryDirectory() as root:
            installed = self.install(root)
            result = run("verify", "linux-perf", "--path", str(installed))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(result.stdout.startswith("ok linux-perf"))

    def test_drift_still_fails_with_the_reason(self):
        with tempfile.TemporaryDirectory() as root:
            installed = self.install(root)
            (installed / "SKILL.md").write_text("tampered\n", encoding="utf-8")
            result = run("verify", "linux-perf", "--path", str(installed), "--quiet")
            self.assertEqual(result.returncode, 1)
            self.assertIn("differs from the catalog", result.stderr)


if __name__ == "__main__":
    unittest.main()
