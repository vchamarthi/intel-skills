"""`intel-skills list` marks a description it had to cut short.

Standard library only, like the rest of this repository's tooling:
`python3 -m unittest discover -s tests` runs it, and so does pytest.
"""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIMIT = 100


@unittest.skipIf(shutil.which("node") is None, "node is not installed")
class ListDescriptionTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "bin").mkdir()
        shutil.copy(ROOT / "bin" / "intel-skills.mjs", self.root / "bin" / "intel-skills.mjs")

    def _skill(self, name: str, description: str) -> None:
        skill = self.root / "skills" / name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: {description}\n---\n\nBody.\n", encoding="utf-8"
        )

    def _list(self) -> dict[str, str]:
        result = subprocess.run(
            ["node", str(self.root / "bin" / "intel-skills.mjs"), "list"],
            capture_output=True,
            text=True,
            check=True,
        )
        rows = (line.split("\t") for line in result.stdout.splitlines())
        return {row[0]: row[3] for row in rows}

    def test_long_description_is_marked_as_cut(self) -> None:
        self._skill("long-one", "word " * 40)
        self._skill("short-one", "Fits easily.")
        shown = self._list()
        self.assertEqual(shown["short-one"], "Fits easily.")
        self.assertTrue(shown["long-one"].endswith("..."))
        self.assertLessEqual(len(shown["long-one"]), LIMIT)

    def test_description_of_exactly_the_limit_is_untouched(self) -> None:
        exact = "x" * LIMIT
        self._skill("exact-one", exact)
        self.assertEqual(self._list()["exact-one"], exact)


if __name__ == "__main__":
    unittest.main()
