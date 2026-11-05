# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

"""Portable consumer configuration keeps qualification choices out of catalog CI."""

import unittest
from pathlib import Path

from test_dokimi_workflow_calls import mappings

ROOT = Path(__file__).resolve().parents[2]


class ConsumerWorkflowBoundaries(unittest.TestCase):
    def test_free_catalog_check_needs_no_model_configuration_or_credentials(self):
        text = (ROOT / '.github/workflows/dokimi.yml').read_text()
        job = text.split('\n  checks:\n', 1)[1].split('\n  model:\n', 1)[0]
        self.assertEqual(mappings(job, 'with')['mode'], 'check')
        self.assertNotIn('secrets:', job)
        self.assertNotIn('vars.', job)
        self.assertNotIn('runs-on:', job)
        self.assertEqual(mappings(job, 'with')['config'], '.github/dokimi/config.yaml')

    def test_manual_runs_take_measurement_choices_from_the_operator(self):
        for filename, job_name in (('dokimi.yml', 'model'), ('dokimi-revalidate.yml', 'revalidate')):
            text = (ROOT / '.github/workflows' / filename).read_text()
            job = text.split(f'\n  {job_name}:\n', 1)[1]
            with self.subTest(workflow=filename):
                self.assertIn("if: github.event_name == 'workflow_dispatch'", job)
                values = mappings(job, 'with')
                for name in ('provider', 'judge-provider', 'model', 'judge-model', 'max-usd'):
                    self.assertEqual(values[name], '${{ inputs.' + name + ' }}')
                self.assertEqual(values['policy'], '${{ vars.DOKIMI_POLICY }}')
                self.assertEqual(values['environment'], '${{ vars.DOKIMI_ENVIRONMENT }}')
                self.assertNotIn('github.repository ==', job)

    def test_only_selected_provider_credentials_cross_the_runtime_boundary(self):
        for filename in ('dokimi.yml', 'dokimi-revalidate.yml'):
            source = (ROOT / '.github/workflows' / filename).read_text()
            credentials = mappings(source, 'secrets')
            self.assertEqual(set(credentials), {'openai-api-key', 'anthropic-api-key',
                                                'DOKIMI_CLAUDE_CODE_OAUTH_TOKEN'})
            for name, provider in (('openai-api-key', 'openai'), ('anthropic-api-key', 'anthropic'),
                                   ('DOKIMI_CLAUDE_CODE_OAUTH_TOKEN', 'claude-cli')):
                expression = credentials[name]
                self.assertIn(f"inputs.provider == '{provider}'", expression)
                self.assertIn(f"inputs.judge-provider == '{provider}'", expression)
                self.assertTrue(expression.endswith("|| '' }}"))
            self.assertNotIn('secrets: inherit', source)

    def test_catalog_mapping_does_not_prescribe_a_measurement_policy(self):
        source = (ROOT / '.github/dokimi/config.yaml').read_text()
        self.assertIn('skills: skills/*', source)
        self.assertNotIn('plan:', source)
        self.assertFalse((ROOT / '.github/dokimi/policy.yaml').exists())
        for filename in ('dokimi-publish.yml', 'dokimi-record.yml'):
            text = (ROOT / '.github/workflows' / filename).read_text()
            self.assertEqual(mappings(text, 'with')['policy-digest'], '${{ vars.DOKIMI_POLICY_DIGEST }}')
