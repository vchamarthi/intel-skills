"""`intel-skills bundles` lists the skills.sh.json bundles with their skills."""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_bundles_lists_every_bundle_with_its_skills():
    result = subprocess.run(
        ["node", str(ROOT / "bin" / "intel-skills.mjs"), "bundles"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    groupings = json.loads((ROOT / "skills.sh.json").read_text())["groupings"]
    expected = [f"{g['title']}\t{len(g['skills'])}\t{','.join(g['skills'])}" for g in groupings]
    assert result.stdout.splitlines() == expected
