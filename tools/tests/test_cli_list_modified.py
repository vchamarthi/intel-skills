"""`intel-skills list --modified` lists only imported skills that differ from their upstream."""

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "bin" / "intel-skills.mjs"


def run(*args):
    return subprocess.run(
        ["node", str(CLI), *args], capture_output=True, text=True, check=False
    )


def names(result):
    return [line.split("\t")[0] for line in result.stdout.splitlines()]


class ListModifiedTest(unittest.TestCase):
    def test_only_imports_with_local_modifications_are_listed(self):
        result = run("list", "--modified")
        self.assertEqual(result.returncode, 0, result.stderr)
        listed = names(result)
        self.assertIn("xpu-system-setup", listed)
        self.assertIn("model-can-it-fit", listed)
        self.assertNotIn("dpnp-quickstart", listed)
        self.assertTrue(all("\timported\t" in line for line in result.stdout.splitlines()))

    def test_list_without_flag_still_prints_the_whole_catalog(self):
        everything = names(run("list"))
        self.assertIn("dpnp-quickstart", everything)
        self.assertGreater(len(everything), len(names(run("list", "--modified"))))


if __name__ == "__main__":
    unittest.main()
