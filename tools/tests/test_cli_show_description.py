"""`intel-skills show <skill> --description` prints only the routing description."""

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "bin" / "intel-skills.mjs"


def run(*args):
    return subprocess.run(
        ["node", str(CLI), *args], capture_output=True, text=True, check=False
    )


class ShowDescriptionTest(unittest.TestCase):
    def test_description_matches_list_column(self):
        listed = run("list")
        self.assertEqual(listed.returncode, 0)
        for line in listed.stdout.splitlines():
            name, _, _, short = line.split("\t")
            shown = run("show", name, "--description")
            self.assertEqual(shown.returncode, 0, shown.stderr)
            text = shown.stdout.strip()
            self.assertTrue(short, name)
            self.assertTrue(text.startswith(short), name)
            self.assertNotIn("\n", text, name)

    def test_flag_before_name(self):
        name = run("list").stdout.splitlines()[0].split("\t")[0]
        a = run("show", name, "--description")
        b = run("show", "--description", name)
        self.assertEqual(a.returncode, 0, a.stderr)
        self.assertEqual(a.stdout, b.stdout)

    def test_unknown_skill_still_fails(self):
        result = run("show", "no-such-skill", "--description")
        self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main()
