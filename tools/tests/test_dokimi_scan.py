# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

"""Non-model CI reports real coverage and preserves every scan's failure."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('dokimi_scan', Path(__file__).parents[1] / 'dokimi_scan.py')
scanner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scanner)


class QueryInputs(unittest.TestCase):
    def test_curated_positive_queries_override_answer_prompts_and_deduplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / 'skills' / 'example' / 'evals'
            directory.mkdir(parents=True)
            (directory / 'trigger_eval_set.json').write_text(json.dumps([
                {'query': 'positive request', 'should_trigger': True},
                {'query': 'positive request', 'should_trigger': True},
                {'query': 'unrelated request', 'should_trigger': False},
            ]))
            (directory / 'evals.json').write_text(json.dumps({'evals': [{'prompt': 'answer task'}]}))
            queries, sources = scanner.collect_queries(root)
            self.assertEqual(queries, {'example': ['positive request']})
            self.assertEqual(sources['example']['kind'], 'trigger positives')

    def test_existing_answer_prompts_are_an_explicit_proxy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / 'skills' / 'new-skill' / 'evals'
            directory.mkdir(parents=True)
            (directory / 'evals.json').write_text(json.dumps({'evals': [{'prompt': 'existing task'}]}))
            queries, sources = scanner.collect_queries(root)
            self.assertEqual(queries, {'new-skill': ['existing task']})
            self.assertEqual(sources['new-skill']['kind'], 'eval prompt proxy')

    def test_invalid_query_files_fail_instead_of_silently_losing_coverage(self):
        for content in ('', 'null', '{}', '[{"query": "x", "should_trigger": "false"}]'):
            with self.subTest(content=content), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                directory = root / 'skills' / 'example' / 'evals'
                directory.mkdir(parents=True)
                (directory / 'trigger_eval_set.json').write_text(content)
                with self.assertRaises(ValueError):
                    scanner.collect_queries(root)

    def test_no_cases_does_not_invent_queries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'skills' / 'example').mkdir(parents=True)
            self.assertEqual(scanner.collect_queries(root), ({}, {}))


class ScanReceipts(unittest.TestCase):
    def executor(self, scan_code=0, empty=False):
        def execute(arguments, log, cwd):
            if arguments[:2] == ['catalog', 'scan']:
                payload = {'skills': [{'name': 'example', 'findings': [{'code': 'link-missing'}]}], 'tasks': []}
                log.write_text(json.dumps(payload) if not empty else '{}')
                return scan_code
            if arguments[:2] == ['catalog', 'eval']:
                directory = Path(arguments[arguments.index('--out-dir') + 1])
                directory.mkdir()
                (directory / 'catalog.json').write_text(json.dumps({'status': 'pass', 'skills': []}))
                return 0
            path = Path(arguments[arguments.index('--out') + 1])
            path.write_text(json.dumps({'n_candidates': 1, 'field': {}, 'result': {'lexical': {'own_rate': {'example': 0.0}, 'n_scored': {'example': 1}}}}))
            return 0
        return execute

    def test_structural_failure_survives_other_success_and_retains_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, out = Path(tmp) / 'source', Path(tmp) / 'reports'
            (root / 'skills' / 'example').mkdir(parents=True)
            code = scanner.scan(root, out, execute=self.executor(scan_code=1))
            results = json.loads((out / 'summary.json').read_text())
            self.assertEqual(code, 1)
            self.assertEqual(results['scan']['status'], 'fail')
            self.assertEqual(results['catalog']['status'], 'pass')
            self.assertEqual(results['routing']['status'], 'skipped')
            self.assertIn('link-missing', (out / 'report.md').read_text())
            self.assertEqual(json.loads((out / 'query-coverage.json').read_text())['without_queries'], ['example'])

    def test_successful_exit_without_a_usable_report_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, out = Path(tmp) / 'source', Path(tmp) / 'reports'
            (root / 'skills').mkdir(parents=True)
            self.assertEqual(scanner.scan(root, out, execute=self.executor(empty=True)), 2)
            self.assertEqual(json.loads((out / 'summary.json').read_text())['scan']['status'], 'fail')

    def test_bad_root_or_reused_output_preserves_existing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, out = Path(tmp) / 'source', Path(tmp) / 'reports'
            out.mkdir()
            marker = out / 'keep.txt'
            marker.write_text('user data')
            with self.assertRaises(ValueError):
                scanner.scan(root, out, execute=self.executor())
            (root / 'skills').mkdir(parents=True)
            with self.assertRaises(FileExistsError):
                scanner.scan(root, out, execute=self.executor())
            self.assertEqual(marker.read_text(), 'user data')

    def test_all_existing_queries_are_measured_and_missing_coverage_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, out = Path(tmp) / 'source', Path(tmp) / 'reports'
            directory = root / 'skills' / 'example' / 'evals'
            directory.mkdir(parents=True)
            (directory / 'evals.json').write_text(json.dumps({'evals': [{'prompt': 'existing request'}]}))
            self.assertEqual(scanner.scan(root, out, execute=self.executor()), 0)
            coverage = json.loads((out / 'query-coverage.json').read_text())
            self.assertEqual(coverage['n_queries'], 1)
            self.assertEqual(coverage['without_queries'], [])
            self.assertEqual(coverage['sources']['example']['kind'], 'eval prompt proxy')
            self.assertEqual(json.loads((out / 'summary.json').read_text())['routing']['status'], 'pass')
            self.assertIn('| example | 1 | 0.0000 | eval prompt proxy |', (out / 'report.md').read_text())


class WorkflowContract(unittest.TestCase):
    def test_workflow_installs_only_upstream_and_has_no_model_or_privileged_path(self):
        root = Path(__file__).resolve().parents[2]
        workflow = (root / '.github/workflows/dokimi.yml').read_text()
        self.assertIn('repository: intel/dokimi', workflow)
        self.assertRegex(workflow, r'ref: [0-9a-f]{40}\n')
        for forbidden in ('/.github/workflows/', 'secrets.', 'vars.', 'workflow_call:', 'workflow_run:', ': write',
                          '--model', '--provider'):
            self.assertNotIn(forbidden, workflow)
        self.assertEqual(sorted(p.name for p in (root / '.github/workflows').glob('dokimi*.yml')), ['dokimi.yml'])
