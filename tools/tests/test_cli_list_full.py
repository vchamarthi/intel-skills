"""`intel-skills list --full` prints each description without the 100-character cut."""

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "bin" / "intel-skills.mjs"


def run(*args):
    return subprocess.run(
        ["node", str(CLI), *args], capture_output=True, text=True, check=False
    )


def rows(output):
    return [line.split("\t", 3) for line in output.splitlines()]


class ListFullTest(unittest.TestCase):
    def test_full_extends_truncated_descriptions(self):
        short = run("list")
        full = run("list", "--full")
        self.assertEqual(short.returncode, 0)
        self.assertEqual(full.returncode, 0)
        short_rows, full_rows = rows(short.stdout), rows(full.stdout)
        self.assertEqual(len(short_rows), len(full_rows))
        self.assertTrue(short_rows)
        longer = 0
        for cut, whole in zip(short_rows, full_rows):
            self.assertEqual(cut[:3], whole[:3])
            self.assertTrue(whole[3].startswith(cut[3]))
            self.assertGreaterEqual(len(whole[3]), len(cut[3]))
            longer += len(whole[3]) > 100
        self.assertGreater(longer, 0)


if __name__ == "__main__":
    unittest.main()
