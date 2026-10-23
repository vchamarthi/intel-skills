"""`--dir=<path>` and `--path=<path>` mean the same as the two-word form."""

import subprocess
import tempfile
import unittest
from pathlib import Path

CLI = Path(__file__).resolve().parents[2] / "bin" / "intel-skills.mjs"


def run(*args):
    return subprocess.run(
        ["node", str(CLI), *args], capture_output=True, text=True, check=False
    )


class EqualsFormTest(unittest.TestCase):
    def test_install_and_verify_accept_equals_form(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run("install", "linux-perf", f"--dir={tmp}")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((Path(tmp) / "linux-perf" / "SKILL.md").exists())
            result = run("verify", "linux-perf", f"--path={tmp}/linux-perf")
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_empty_value_is_refused(self):
        result = run("install", "linux-perf", "--dir=")
        self.assertEqual(result.returncode, 1)
        self.assertIn("--dir requires a value", result.stderr)

    def test_unknown_target_in_equals_form_is_named(self):
        result = run("install", "linux-perf", "--target=nope")
        self.assertEqual(result.returncode, 1)
        self.assertIn("unknown target: nope", result.stderr)


if __name__ == "__main__":
    unittest.main()
