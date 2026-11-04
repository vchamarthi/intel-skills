# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

"""Catalog wiring keeps implemented tasks attributable and CI opt-in for spend."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import validate_skills as v


class CatalogRuntimeWiring(unittest.TestCase):
    def test_existing_launch_and_routing_tasks_are_claimed_by_their_suite(self):
        names = {p.name: "tool-skill" for p in v.SKILLS_DIR.iterdir() if p.is_dir()}
        report = v.Report()
        imported = {name for name in names if (v.SKILLS_DIR / name / ".source.json").is_file()}
        v.check_suites({}, names, imported, report)
        self.assertEqual(report.errors, [])
        unresolved = [warning for warning in report.warnings
                      if any(name in warning for name in ("ai-inference-deploy", "openvino-gpu-run"))
                      and ("no suite" in warning or "no suite lists" in warning)]
        self.assertEqual(unresolved, [])


if __name__ == "__main__":
    unittest.main()


class ConsumerWorkflowBoundaries(unittest.TestCase):
    def test_paid_work_is_manual_and_publisher_has_no_candidate_checkout(self):
        root = Path(__file__).resolve().parents[2]
        workflow = (root / ".github/workflows/dokimi.yml").read_text()
        publisher = (root / ".github/workflows/dokimi-publish.yml").read_text()
        self.assertIn("mode: check", workflow)
        self.assertIn("mode: run", workflow)
        self.assertIn("github.event_name == 'workflow_dispatch'", workflow)
        self.assertNotIn("pull_request_target", workflow + publisher)
        self.assertNotIn("actions/checkout", publisher)
        self.assertNotIn("secrets:", publisher)
        self.assertIn("source-workflow: .github/workflows/dokimi.yml", publisher)

    def test_oracle_job_is_native_x86_and_has_no_model_credentials(self):
        root = Path(__file__).resolve().parents[2]
        job = (root / ".github/workflows/dokimi.yml").read_text().split("  dpnp-oracles:", 1)[1]
        self.assertIn("runs-on: ubuntu-24.04", job)
        self.assertIn("needs: checks", job)
        self.assertIn("persist-credentials: false", job)
        self.assertIn("tools/run_dpnp_oracles.py", job)
        self.assertNotIn("secrets.", job)
        self.assertNotIn(": write", job)


class EnvironmentSubscriptionSecret(unittest.TestCase):
    def test_model_and_revalidation_forward_the_environment_secret_by_its_own_name(self):
        root = Path(__file__).resolve().parents[2]
        for name in ("dokimi.yml", "dokimi-revalidate.yml"):
            text = (root / ".github/workflows" / name).read_text()
            self.assertIn("environment: dokimi-live", text)
            self.assertIn("DOKIMI_CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.DOKIMI_CLAUDE_CODE_OAUTH_TOKEN }}", text)
            self.assertNotIn("claude-code-oauth-token:", text)
        free = (root / ".github/workflows/dokimi.yml").read_text().split("  model:", 1)[0]
        self.assertNotIn("secrets:", free)
