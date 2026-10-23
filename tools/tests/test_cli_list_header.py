"""`intel-skills list --header` prefixes the tab-separated listing with column names."""

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "bin" / "intel-skills.mjs"


def run(*args):
    return subprocess.run(
        ["node", str(CLI), *args], capture_output=True, text=True, check=False
    )


class ListHeaderTest(unittest.TestCase):
    def test_header_precedes_unchanged_rows(self):
        plain = run("list")
        headed = run("list", "--header")
        self.assertEqual(plain.returncode, 0, plain.stderr)
        self.assertEqual(headed.returncode, 0, headed.stderr)
        lines = headed.stdout.splitlines()
        self.assertEqual(lines[0], "name\torigin\tpin\tdescription")
        self.assertEqual("\n".join(lines[1:]) + "\n", plain.stdout)

    def test_header_matches_row_column_count(self):
        lines = run("list", "--header").stdout.splitlines()
        columns = {line.count("\t") for line in lines}
        self.assertEqual(columns, {3})

    def test_plain_list_has_no_header(self):
        first = run("list").stdout.splitlines()[0]
        self.assertNotEqual(first.split("\t")[0], "name")


if __name__ == "__main__":
    unittest.main()
