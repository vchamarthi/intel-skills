"""`intel-skills list --names` prints bare skill names, one per line."""

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "bin" / "intel-skills.mjs"


def run(*args):
    return subprocess.run(
        ["node", str(CLI), *args], capture_output=True, text=True, check=False
    )


class ListNamesTest(unittest.TestCase):
    def test_names_matches_first_column_of_list(self):
        table = run("list")
        names = run("list", "--names")
        self.assertEqual(table.returncode, 0)
        self.assertEqual(names.returncode, 0)
        expected = [line.split("\t")[0] for line in table.stdout.splitlines()]
        self.assertTrue(expected)
        self.assertEqual(names.stdout.splitlines(), expected)
        self.assertNotIn("\t", names.stdout)


if __name__ == "__main__":
    unittest.main()
