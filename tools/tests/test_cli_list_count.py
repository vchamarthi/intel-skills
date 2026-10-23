"""`intel-skills list --count` prints how many skills the catalog holds."""

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "bin" / "intel-skills.mjs"


def run(*args):
    return subprocess.run(["node", str(CLI), *args], capture_output=True, text=True, check=False)


class ListCountTest(unittest.TestCase):
    def test_count_matches_listed_rows(self):
        rows = run("list").stdout.splitlines()
        result = run("list", "--count")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), str(len(rows)))


if __name__ == "__main__":
    unittest.main()
