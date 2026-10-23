"""`intel-skills list --from <repo>` shows only the skills imported from that repository.

Standard library only, like the rest of the tooling: `python3 -m unittest discover -s tests`.
"""

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "bin" / "intel-skills.mjs"


def run(*args):
    return subprocess.run(["node", str(CLI), *args], capture_output=True, text=True, check=False)


def upstreams():
    """skill name -> upstream repository name, read from each .source.json."""
    found = {}
    for path in (ROOT / "skills").glob("*/.source.json"):
        found[path.parent.name] = json.loads(path.read_text())["repo"].rstrip("/").split("/")[-1]
    return found


class ListFrom(unittest.TestCase):
    def test_from_keeps_only_that_upstream(self):
        imported = upstreams()
        repo = imported["linux-perf"]
        expected = sorted(name for name, origin in imported.items() if origin == repo)
        result = run("list", "--from", repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([line.split("\t")[0] for line in result.stdout.splitlines()], expected)
        self.assertLess(len(expected), len(imported), "needs a second upstream to prove the filter")

    def test_from_unknown_repo_fails(self):
        result = run("list", "--from", "no-such-repo")
        self.assertEqual(result.returncode, 1)
        self.assertIn("no skills imported from no-such-repo", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_from_requires_a_value(self):
        result = run("list", "--from")
        self.assertEqual(result.returncode, 1)
        self.assertIn("--from requires a value", result.stderr)

    def test_plain_list_is_unchanged(self):
        result = run("list")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(result.stdout.splitlines()), len(list((ROOT / "skills").glob("*/SKILL.md"))))


if __name__ == "__main__":
    unittest.main()
