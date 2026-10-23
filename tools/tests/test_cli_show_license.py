"""`intel-skills show <skill> --license` prints only the skill's licence."""

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "bin" / "intel-skills.mjs"
SKILLS = ROOT / "skills"


def run(*args):
    return subprocess.run(
        ["node", str(CLI), *args], capture_output=True, text=True, check=False
    )


class ShowLicenseTest(unittest.TestCase):
    def test_every_skill_prints_one_licence_line(self):
        for skill in sorted(SKILLS.glob("*/SKILL.md")):
            name = skill.parent.name
            shown = run("show", name, "--license")
            self.assertEqual(shown.returncode, 0, shown.stderr)
            lines = shown.stdout.splitlines()
            self.assertEqual(len(lines), 1, name)
            source = skill.parent / ".source.json"
            if source.exists():
                expected = json.loads(source.read_text(encoding="utf-8"))["license"]
            else:
                expected = "Apache-2.0"
            self.assertEqual(lines[0], expected, name)

    def test_flag_before_name(self):
        name = sorted(SKILLS.glob("*/SKILL.md"))[0].parent.name
        a = run("show", name, "--license")
        b = run("show", "--license", name)
        self.assertEqual(a.returncode, 0, a.stderr)
        self.assertEqual(a.stdout, b.stdout)

    def test_unknown_skill_still_fails(self):
        result = run("show", "no-such-skill", "--license")
        self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main()
