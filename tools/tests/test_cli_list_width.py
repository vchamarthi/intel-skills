"""`intel-skills list --width <n>` sets how much of each description is printed."""

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "bin" / "intel-skills.mjs"


def run(*args):
    return subprocess.run(
        ["node", str(CLI), *args], capture_output=True, text=True, check=False
    )


def descriptions(output):
    return [line.split("\t", 3)[3] for line in output.splitlines()]


class ListWidthTest(unittest.TestCase):
    def test_width_cuts_each_description(self):
        result = run("list", "--width", "20")
        self.assertEqual(result.returncode, 0)
        cut = descriptions(result.stdout)
        self.assertTrue(cut)
        self.assertTrue(all(len(text) <= 20 for text in cut))

    def test_width_beyond_default_extends_descriptions(self):
        default = descriptions(run("list").stdout)
        wide = descriptions(run("list", "--width", "400").stdout)
        self.assertEqual(len(default), len(wide))
        self.assertTrue(all(w.startswith(d) for d, w in zip(default, wide)))
        self.assertTrue(any(len(w) > 100 for w in wide))

    def test_invalid_width_is_rejected(self):
        for value in ("0", "-3", "abc", "1.5"):
            result = run("list", "--width", value)
            self.assertEqual(result.returncode, 1, value)
            self.assertIn("--width must be a positive integer", result.stderr)
            self.assertEqual(result.stdout, "")

    def test_width_without_value_is_rejected(self):
        result = run("list", "--width")
        self.assertEqual(result.returncode, 1)
        self.assertIn("--width requires a value", result.stderr)


if __name__ == "__main__":
    unittest.main()
