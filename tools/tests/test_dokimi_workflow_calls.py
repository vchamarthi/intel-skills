# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

"""Thin consumer calls match the workflow_call interfaces captured from the pinned engine."""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = json.loads((Path(__file__).parent / "fixtures/dokimi-workflow-contracts.json").read_text())


def mappings(text, field, indent=4):
    lines = text.splitlines()
    values = {}
    active = False
    for line in lines:
        if line == " " * indent + field + ":":
            active = True
            continue
        if active and line.strip() and not line.startswith(" " * (indent + 2)):
            break
        match = re.fullmatch(" " * (indent + 2) + r"([A-Za-z_][A-Za-z0-9_-]*): (.+)", line)
        if active and match:
            values[match[1]] = match[2]
    return values


def dispatch_types(text):
    header = text.split("\npermissions:", 1)[0]
    return dict(re.findall(r"(?m)^      ([a-z][a-z0-9-]*):\n(?:        [^\n]*\n)*?        type: (string|number|boolean)\n", header))


def value_type(value, dispatch):
    normalized = re.fullmatch(r"\$\{\{ fromJSON\(inputs\.([a-z][a-z0-9-]*)(?: \|\| '0')?\) \}\}", value)
    if normalized:
        return dispatch[normalized[1]]
    direct = re.fullmatch(r"\$\{\{ inputs\.([a-z][a-z0-9-]*) \}\}", value)
    if direct:
        return "string"
    if value in ("true", "false"):
        return "boolean"
    if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value):
        return "number"
    return "string"


class PinnedWorkflowCalls(unittest.TestCase):
    def test_every_stage_has_a_consumer_matching_the_pinned_interface(self):
        expected = {"dokimi.yml", "dokimi-publish.yml", "dokimi-record.yml", "dokimi-revalidate.yml"}
        directory = ROOT / ".github/workflows"
        self.assertFalse(expected - {path.name for path in directory.glob("dokimi*.yml")})
        for filename in sorted(expected):
            text = (directory / filename).read_text()
            jobs = re.split(r"(?m)^  [a-z][a-z0-9-]*:\n", text.split("\njobs:\n", 1)[1])[1:]
            for job in jobs:
                match = re.search(r"(?m)^    uses: ([^\n]+)$", job)
                if not match:
                    continue
                with self.subTest(file=filename, target=match[1]):
                    repository, workflow, commit = re.fullmatch(
                        r"([^/]+/[^/]+)/.github/workflows/([^@]+)@([0-9a-f]{40})", match[1]).groups()
                    self.assertEqual(repository, CONTRACT["repository"])
                    self.assertEqual(commit, CONTRACT["commit"])
                    contract = CONTRACT["workflows"][workflow]
                    allowed = (mappings(job, "permissions") if re.search(r"(?m)^    permissions:", job)
                               else mappings(text, "permissions", indent=0))
                    ranks = {"none": 0, "read": 1, "write": 2}
                    for nested, permissions in contract["job_permissions"].items():
                        for permission, level in permissions.items():
                            self.assertLessEqual(ranks[level], ranks[allowed.get(permission, "none")],
                                                 f"{filename}: nested {nested} requires {permission}:{level}, regardless of its condition")
                    values = mappings(job, "with")
                    self.assertFalse(set(values) - set(contract["inputs"]))
                    required = {key for key, spec in contract["inputs"].items() if spec["required"]}
                    self.assertFalse(required - set(values))
                    self.assertFalse(set(mappings(job, "secrets")) - set(contract["secrets"]))
                    dispatch = dispatch_types(text)
                    for key, value in values.items():
                        self.assertEqual(value_type(value, dispatch), contract["inputs"][key]["type"], key)
                    if "dokimi-ref" in values:
                        self.assertEqual(values["dokimi-ref"], commit)

    def test_numeric_dispatch_strings_are_normalized_before_number_typed_calls(self):
        serialized = {"pr-number": "7", "reps": "2", "max-calls": "90"}
        cases = {"dokimi.yml": "model", "dokimi-revalidate.yml": "revalidate"}
        for filename, job in cases.items():
            source = (ROOT / ".github/workflows" / filename).read_text()
            text = re.split(rf"(?m)^  {job}:\n", source, maxsplit=1)[1]
            arguments = mappings(text, "with")
            keys = set(serialized) if job == "model" else {"reps", "max-calls"}
            for key in keys:
                with self.subTest(workflow=filename, input=key):
                    expression = re.fullmatch(r"\$\{\{ fromJSON\(inputs\.([a-z][a-z0-9-]*)(?: \|\| '0')?\) \}\}", arguments[key])
                    self.assertIsNotNone(expression, "dispatch strings need explicit fromJSON at typed workflow boundary")
                    decoded = json.loads(serialized[expression[1]])
                    self.assertEqual(type(decoded), int)
                    self.assertEqual(decoded, int(serialized[key]))

    def test_record_is_manual_and_scopes_content_write_to_the_record_job(self):
        text = (ROOT / ".github/workflows/dokimi-record.yml").read_text()
        self.assertIn("  workflow_dispatch:", text)
        self.assertNotIn("  push:", text)
        self.assertNotIn("  schedule:", text)
        self.assertIn("permissions: {}", text)
        self.assertEqual(text.count("contents: write"), 1)
        self.assertIn("commit-author: ${{ github.actor }}", text)
        self.assertIn("github.actor_id, github.actor", text)
        self.assertIn("source-workflow: .github/workflows/dokimi.yml", text)
        self.assertIn("expect-previous: ${{ inputs.expect-previous }}", text)
        self.assertNotIn("secrets:", text)

    def test_revalidation_is_manual_configurable_and_cannot_write(self):
        text = (ROOT / ".github/workflows/dokimi-revalidate.yml").read_text()
        self.assertIn("  workflow_dispatch:", text)
        self.assertNotIn("  schedule:", text)
        self.assertNotIn(": write", text)
        self.assertIn("provider: ${{ inputs.provider }}", text)
        self.assertIn("judge-provider: ${{ inputs.judge-provider }}", text)
        self.assertIn("max-calls: ${{ fromJSON(inputs.max-calls || '0') }}", text)
        self.assertIn("max-usd: ${{ inputs.max-usd }}", text)
        self.assertIn("revision: ${{ inputs.revision }}", text)
        self.assertIn("baseline: ${{ inputs.baseline }}", text)


class SecretMappingParser(unittest.TestCase):
    def test_uppercase_environment_secret_names_are_checked_against_the_pinned_contract(self):
        text = "    secrets:\n      DOKIMI_CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.DOKIMI_CLAUDE_CODE_OAUTH_TOKEN }}\n"
        self.assertEqual(mappings(text, "secrets"), {
            "DOKIMI_CLAUDE_CODE_OAUTH_TOKEN": "${{ secrets.DOKIMI_CLAUDE_CODE_OAUTH_TOKEN }}"})


if __name__ == "__main__":
    unittest.main()
