"""`intel-skills list` marks a description it had to cut short."""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
LIMIT = 100


def _skill(root: Path, name: str, description: str) -> None:
    skill = root / "skills" / name
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\nBody.\n", encoding="utf-8"
    )


def _list(tmp_path: Path) -> dict[str, str]:
    (tmp_path / "bin").mkdir()
    shutil.copy(ROOT / "bin" / "intel-skills.mjs", tmp_path / "bin" / "intel-skills.mjs")
    result = subprocess.run(
        ["node", str(tmp_path / "bin" / "intel-skills.mjs"), "list"],
        capture_output=True,
        text=True,
        check=True,
    )
    rows = (line.split("\t") for line in result.stdout.splitlines())
    return {row[0]: row[3] for row in rows}


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_long_description_is_marked_as_cut(tmp_path: Path) -> None:
    _skill(tmp_path, "long-one", "word " * 40)
    _skill(tmp_path, "short-one", "Fits easily.")
    shown = _list(tmp_path)
    assert shown["short-one"] == "Fits easily."
    assert shown["long-one"].endswith("...")
    assert len(shown["long-one"]) <= LIMIT


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_description_of_exactly_the_limit_is_untouched(tmp_path: Path) -> None:
    exact = "x" * LIMIT
    _skill(tmp_path, "exact-one", exact)
    assert _list(tmp_path)["exact-one"] == exact
