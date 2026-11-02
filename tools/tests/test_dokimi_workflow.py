# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

"""Run the workflow's exact shell blocks; optional installed-wheel integration.

DOKIMI_TEST_BIN=/absolute/path/to/venv/bin/dokimi enables real CLI scenarios.
These tests do not emulate GitHub checkout, permissions or artifact transport.
"""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/dokimi.yml"


def shell_step(step_id):
    """Read a literal run block without requiring YAML in the stdlib tool suite."""
    assert WORKFLOW.is_file(), "static consumer workflow is missing"
    source = WORKFLOW.read_text()
    match = re.search(r"^        id: " + step_id + r"\n(?:(?!^      - ).)*?^        run: \|\n((?:          [^\n]*\n|\n)+)", source, re.M | re.S)
    if not match:
        raise AssertionError(f"missing literal shell step {step_id}")
    return "\n".join(line[10:] if line else "" for line in match[1].splitlines())


class ShellCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="dokimi workflow ")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.env = {**os.environ, "GITHUB_OUTPUT": str(self.root / "output"),
                    "GITHUB_STEP_SUMMARY": str(self.root / "summary"),
                    "RUNNER_TEMP": str(self.root), "GITHUB_WORKSPACE": str(self.root),
                    "EVENT_NAME": "workflow_dispatch", "PR_BASE_SHA": "", "PUSH_BEFORE": "",
                    "BASE_REF": "", "PYTHONPATH": "", "PYTHONSAFEPATH": "1"}

    def run_step(self, step_id, **env):
        return subprocess.run(["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", shell_step(step_id)],
                              env={**self.env, **env}, cwd=self.root, text=True, capture_output=True)


class WorkflowShellTests(ShellCase):
    def test_event_base_selection_and_multiline_injection_rejection(self):
        for event, pr, push, expected in [
            ("pull_request", "a" * 40, "b" * 40, "a" * 40),
            ("push", "a" * 40, "b" * 40, "b" * 40),
            ("workflow_dispatch", "a" * 40, "b" * 40, ""),
            ("push", "", "0" * 40, "unavailable"),
            ("pull_request", "$(touch injected)\nref=evil", "", "unavailable"),
        ]:
            with self.subTest(event=event, base=pr):
                Path(self.env["GITHUB_OUTPUT"]).unlink(missing_ok=True)
                result = self.run_step("base", EVENT_NAME=event, PR_BASE_SHA=pr, PUSH_BEFORE=push)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(Path(self.env["GITHUB_OUTPUT"]).read_text(), f"ref={expected}\n")
                self.assertFalse((self.root / "injected").exists())

    def test_missing_report_summary_is_explicit(self):
        (self.root / "dokimi-status.txt").write_text("2\n")
        result = self.run_step("summary")
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = Path(self.env["GITHUB_STEP_SUMMARY"]).read_text()
        self.assertIn("Static checks only", summary)
        self.assertIn("No report was produced", summary)
        self.assertIn("2", summary)

    def test_report_summary_preserves_failure_report(self):
        receipts = self.root / "dokimi-receipts"
        receipts.mkdir()
        (receipts / "report.md").write_text("catalog validation failed\n")
        (self.root / "dokimi-status.txt").write_text("1\n")
        result = self.run_step("summary")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("catalog validation failed", Path(self.env["GITHUB_STEP_SUMMARY"]).read_text())

    def test_workflow_trust_boundary_and_failure_receipts(self):
        self.assertTrue(WORKFLOW.is_file(), "static consumer workflow is missing")
        source = WORKFLOW.read_text()
        self.assertNotIn("pull_request_target", source)
        self.assertNotIn("secrets.", source)
        self.assertRegex(source, r"permissions:\n  contents: read\n")
        self.assertEqual(source.count("persist-credentials: false"), 2)
        self.assertIn("repository: vchamarthi/dokimi", source)
        self.assertRegex(source, r"ref: [0-9a-f]{40}\n")
        self.assertIn("fetch-depth: 0", source)
        self.assertIn("python-version: '3.13'", source)
        self.assertIn("path: consumer", source)
        self.assertIn("path: framework", source)
        self.assertIn("--require-hashes", shell_step("install"))
        self.assertIn("--no-build-isolation", shell_step("install"))
        self.assertIn("--no-deps", shell_step("install"))
        self.assertNotIn("consumer", shell_step("install"))
        for step in ("base", "install", "evaluate", "summary"):
            self.assertNotIn("${{", shell_step(step), step)
        self.assertNotIn("continue-on-error", source)
        self.assertIn('exit "$status"', shell_step("evaluate"))
        self.assertGreaterEqual(source.count("if: always()"), 2)
        self.assertIn("${{ runner.temp }}/dokimi-receipts/", source)
        self.assertIn("${{ runner.temp }}/dokimi-status.txt", source)
        for action in re.findall(r"uses: (\S+)", source):
            self.assertRegex(action, r"@[0-9a-f]{40}$")


@unittest.skipUnless(os.environ.get("DOKIMI_TEST_BIN"), "set DOKIMI_TEST_BIN to an installed candidate wheel CLI")
class InstalledWorkflowTests(ShellCase):
    """The consumer is data; all executable code comes from the installed wheel."""

    def setUp(self):
        super().setUp()
        self.cli = Path(os.environ["DOKIMI_TEST_BIN"]).resolve()
        self.assertTrue(self.cli.is_file())
        self.consumer = self.root / "consumer"
        subprocess.run(["git", "clone", "--quiet", "--no-hardlinks", str(ROOT), str(self.consumer)], check=True)
        self.base = subprocess.check_output(["git", "-C", str(self.consumer), "rev-parse", "HEAD"], text=True).strip()
        target = self.root / "dokimi-venv/bin/dokimi"
        target.parent.mkdir(parents=True)
        target.symlink_to(self.cli)
        self.receipts = self.root / "dokimi-receipts"
        self.runs = 0

    def evaluate(self, expected, base=""):
        Path(self.env["GITHUB_STEP_SUMMARY"]).unlink(missing_ok=True)
        catalog_before = (self.consumer / "skills.yaml").read_bytes()
        result = self.run_step("evaluate", BASE_REF=base)
        self.assertEqual((self.consumer / "skills.yaml").read_bytes(), catalog_before)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        self.assertEqual((self.root / "dokimi-status.txt").read_text(), f"{expected}\n")
        summary = self.run_step("summary")
        self.assertEqual(summary.returncode, 0, summary.stderr)
        self.runs += 1
        evidence = os.environ.get("DOKIMI_TEST_RECEIPTS")
        if evidence:
            destination = Path(evidence) / self._testMethodName / str(self.runs)
            destination.mkdir(parents=True)
            for name in ("dokimi-receipts", "dokimi-status.txt", "summary"):
                item = self.root / name
                if item.is_dir():
                    shutil.copytree(item, destination / name)
                elif item.is_file():
                    shutil.copyfile(item, destination / name)
            (destination / "process.json").write_text(json.dumps({"exit": result.returncode, "stdout": result.stdout,
                                                                  "stderr": result.stderr, "base": base}) + "\n")
        if expected != 2:
            self.assertEqual({p.name for p in self.receipts.iterdir()}, {"catalog.json", "plan.json", "result.json", "report.md"})
            data = json.loads((self.receipts / "catalog.json").read_text())
            self.assertEqual(data["tier"], "static")
            plan = json.loads((self.receipts / "plan.json").read_text())
            result_data = json.loads((self.receipts / "result.json").read_text())
            self.assertEqual({c["cell_id"] for c in plan["cells"]}, {c["cell_id"] for c in result_data["cells"]})
            self.assertEqual(len(plan["cells"]), 1 + len(data["selection"]["selected"]))
            self.assertTrue(all(c["model"] is None for c in result_data["cells"]))
            self.assertEqual(data["source"]["commit"], self.base)
            return data
        return None

    def test_full_catalog_and_missing_base(self):
        data = self.evaluate(0)
        self.assertEqual(len(data["skills"]), 35)
        tasks = [task for row in data["skills"] for task in row["tasks"]]
        self.assertEqual(len(tasks), 17)
        self.assertEqual(sum(not task["declared"] for task in tasks), 2)
        self.assertEqual({row["evaluation"] for row in data["skills"]}, {"checks_only", "no_tasks", "not_measured"})
        self.assertEqual(data["status"], "pass")
        all_names = data["selection"]["selected"]
        missing = self.evaluate(0, "f" * 40)
        self.assertEqual(missing["selection"]["selected"], all_names)

    def test_resource_task_shared_registry_docs_deletion_and_rename(self):
        # Restore working bytes between cases, while keeping one actual Git base.
        resource = next((self.consumer / "skills/dpnp-quickstart/references").glob("*.md"))
        cases = [
            (str(resource.relative_to(self.consumer)), "edit", ["dpnp-quickstart"]),
            ("evaluation/harbor/tasks/dpnp-fft-pipeline/instruction.md", "edit", ["dpnp-quickstart"]),
            ("skills.yaml", "edit", None),
            (".github/workflows/validate.yml", "edit", None),
            ("README.md", "edit", []),
            (str(resource.relative_to(self.consumer)), "delete", ["dpnp-quickstart"]),
            (str(resource.relative_to(self.consumer)), "rename", ["dpnp-quickstart"]),
        ]
        for relative, action, selected in cases:
            with self.subTest(path=relative, action=action):
                subprocess.run(["git", "-C", str(self.consumer), "reset", "--hard", "--quiet", self.base], check=True)
                subprocess.run(["git", "-C", str(self.consumer), "clean", "-fdq"], check=True)
                path = self.consumer / relative
                if action == "delete":
                    path.unlink()
                elif action == "rename":
                    subprocess.run(["git", "-C", str(self.consumer), "mv", relative, relative + " renamed é.md"], check=True)
                else:
                    with path.open("a") as stream:
                        stream.write("\n# local workflow test\n")
                # Catalog integrity runs even when no skill check is selected.
                data = self.evaluate(0, self.base)
                if selected is None:
                    self.assertEqual(len(data["selection"]["selected"]), len(data["skills"]))
                else:
                    self.assertEqual(data["selection"]["selected"], selected)

    def test_malformed_metadata_then_repair_has_fresh_receipts(self):
        catalog = self.consumer / "skills.yaml"
        original = catalog.read_bytes()
        self.evaluate(0, self.base)
        catalog.write_text("skills: [broken\n")
        self.evaluate(2, self.base)
        self.assertFalse((self.receipts / "result.json").exists())
        catalog.write_bytes(original)
        self.evaluate(0, self.base)
        self.assertIn("Static checks only", Path(self.env["GITHUB_STEP_SUMMARY"]).read_text())

    def test_missing_implemented_task_and_escape_fail(self):
        task = self.consumer / "evaluation/harbor/tasks/dpnp-fft-pipeline"
        shutil.rmtree(task)
        data = self.evaluate(1, self.base)
        self.assertEqual(data["status"], "fail")
        subprocess.run(["git", "-C", str(self.consumer), "reset", "--hard", "--quiet", self.base], check=True)
        skill = self.consumer / "skills/dpnp-quickstart"
        shutil.rmtree(skill)
        skill.symlink_to(self.root)
        data = self.evaluate(1, self.base)
        self.assertIn("unsafe-path", {item["code"] for item in data["problems"]})

    def test_payload_and_shell_metacharacters_are_data(self):
        marker = self.root / "injected"
        payload = self.consumer / "skills/dpnp-quickstart/scripts/$(touch injected); é\nresource.py"
        payload.parent.mkdir(exist_ok=True)
        payload.write_text(f"from pathlib import Path\nPath({str(marker)!r}).touch()\n")
        (self.consumer / "sitecustomize.py").write_text(payload.read_text())
        (self.consumer / "setup.py").write_text(payload.read_text())
        callback = self.root / "git callback.sh"
        callback.write_text(f"#!/bin/sh\ntouch '{marker}'\n")
        callback.chmod(0o755)
        for setting in ("core.fsmonitor", "diff.external"):
            subprocess.run(["git", "-C", str(self.consumer), "config", setting, str(callback)], check=True)
        data = self.evaluate(0, self.base)
        self.assertIn("dpnp-quickstart", data["selection"]["selected"])
        self.assertFalse(marker.exists())
        self.evaluate(0, "$(touch injected); --help")
        self.assertFalse(marker.exists())

    def test_output_source_overlap_is_rejected(self):
        # RUNNER_TEMP is a caller-owned location; deliberate overlap must still be rejected.
        overlap = self.consumer / "skills/dpnp-quickstart"
        target = overlap / "dokimi-venv/bin/dokimi"
        target.parent.mkdir(parents=True)
        target.symlink_to(self.cli)
        result = self.run_step("evaluate", RUNNER_TEMP=str(overlap), BASE_REF=self.base)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertFalse((overlap / "dokimi-receipts/catalog.json").exists())
        self.assertEqual((overlap / "dokimi-status.txt").read_text(), "2\n")
        summary = self.run_step("summary", RUNNER_TEMP=str(overlap))
        self.assertEqual(summary.returncode, 0, summary.stderr)
        self.assertIn("No report was produced", Path(self.env["GITHUB_STEP_SUMMARY"]).read_text())
        evidence = os.environ.get("DOKIMI_TEST_RECEIPTS")
        if evidence:
            destination = Path(evidence) / self._testMethodName / "1"
            destination.mkdir(parents=True)
            shutil.copyfile(overlap / "dokimi-status.txt", destination / "dokimi-status.txt")
            shutil.copyfile(Path(self.env["GITHUB_STEP_SUMMARY"]), destination / "summary")
            (destination / "process.json").write_text(json.dumps({"exit": result.returncode, "stdout": result.stdout,
                                                                  "stderr": result.stderr, "base": self.base}) + "\n")


if __name__ == "__main__":
    unittest.main()
