"""`install <skill> --all` is ambiguous, so it is refused instead of ignoring the name."""

import subprocess
import tempfile
import unittest
from pathlib import Path

CLI = Path(__file__).resolve().parents[2] / "bin" / "intel-skills.mjs"


def run(*args):
    return subprocess.run(
        ["node", str(CLI), *args], capture_output=True, text=True, check=False
    )


class InstallAllWithNameTest(unittest.TestCase):
    def test_name_and_all_together_is_an_error_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run("install", "linux-perf", "--all", "--dir", tmp)
            self.assertEqual(result.returncode, 1)
            self.assertIn("not both", result.stderr)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_all_alone_still_installs_everything(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run("install", "--all", "--dir", tmp)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((Path(tmp) / "linux-perf" / "SKILL.md").exists())


if __name__ == "__main__":
    unittest.main()
