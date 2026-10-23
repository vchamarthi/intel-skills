"""`intel-skills verify --json` reports the comparison as one JSON object."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "bin" / "intel-skills.mjs"
SKILL = "linux-perf"


def run(*args):
    return subprocess.run(["node", str(CLI), *args], capture_output=True, text=True, check=False)


class VerifyJsonTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.assertEqual(run("install", SKILL, "--dir", tmp.name).returncode, 0)
        self.installed = Path(tmp.name) / SKILL

    def test_matching_install_reports_ok(self):
        result = run("verify", SKILL, "--path", str(self.installed), "--json")
        self.assertEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertEqual(report["skill"], SKILL)
        self.assertIs(report["ok"], True)
        self.assertEqual(report["problems"], [])
        self.assertGreater(report["files"], 0)

    def test_altered_install_lists_every_problem_and_exits_nonzero(self):
        with (self.installed / "SKILL.md").open("a") as handle:
            handle.write("\nextra\n")
        for index in range(5):
            (self.installed / f"stray-{index}.md").write_text("x")
        result = run("verify", SKILL, "--path", str(self.installed), "--json")
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertIs(report["ok"], False)
        self.assertIn("SKILL.md differs from the catalog", report["problems"])
        self.assertEqual(len(report["problems"]), 6)

    def test_failure_before_the_comparison_still_prints_json(self):
        result = run("verify", SKILL, "--path", str(self.installed / "missing"), "--json")
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertIs(report["ok"], False)
        self.assertIn("no such directory", report["error"])
        no_path = run("verify", SKILL, "--json")
        self.assertEqual(no_path.returncode, 1)
        self.assertIn("--path", json.loads(no_path.stdout)["error"])
        unknown = run("verify", "no-such-skill", "--path", str(self.installed), "--json")
        self.assertEqual(unknown.returncode, 1)
        self.assertIn("skill not found", json.loads(unknown.stdout)["error"])

    def test_text_output_is_unchanged_without_the_flag(self):
        result = run("verify", SKILL, "--path", str(self.installed))
        self.assertEqual(result.returncode, 0)
        self.assertTrue(result.stdout.startswith(f"ok {SKILL} ("))


if __name__ == "__main__":
    unittest.main()
