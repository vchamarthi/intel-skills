"""`intel-skills list --class <hw-class>` keeps the skills skills.yaml files under that class."""

import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "bin" / "intel-skills.mjs"


def run(*args):
    return subprocess.run(["node", str(CLI), *args], capture_output=True, text=True, check=False)


def catalog_classes():
    """name -> intel-hw-class, read independently of the CLI."""
    classes = {}
    name = None
    for line in (ROOT / "skills.yaml").read_text(encoding="utf8").splitlines():
        match = re.match(r"- name: (\S+)", line)
        if match:
            name = match.group(1)
            continue
        match = re.match(r'\s+intel-hw-class: "?([a-z]+)"?', line)
        if match and name:
            classes[name] = match.group(1)
    return classes


class ListClassTest(unittest.TestCase):
    def test_class_keeps_only_matching_skills(self):
        classes = catalog_classes()
        wanted = sorted(name for name, hw in classes.items() if hw == "gpu")
        self.assertTrue(wanted)
        result = run("list", "--class", "gpu")
        self.assertEqual(result.returncode, 0, result.stderr)
        listed = [line.split("\t")[0] for line in result.stdout.splitlines()]
        self.assertEqual(listed, wanted)

    def test_equals_form(self):
        self.assertEqual(run("list", "--class=gpu").stdout, run("list", "--class", "gpu").stdout)

    def test_unknown_class_is_rejected(self):
        result = run("list", "--class", "quantum")
        self.assertEqual(result.returncode, 1)
        self.assertIn("unknown class: quantum", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_missing_value_is_rejected(self):
        result = run("list", "--class")
        self.assertEqual(result.returncode, 1)
        self.assertIn("--class requires a value", result.stderr)


if __name__ == "__main__":
    unittest.main()
