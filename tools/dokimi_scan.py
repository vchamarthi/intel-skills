# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

"""Run Dokimi's offline catalog checks and preserve their reports for CI."""

import argparse
from collections import Counter
import json
import html
import os
from pathlib import Path
import subprocess
import sys


def collect_queries(root):
    queries, sources = {}, {}
    if (root / 'skills').is_symlink():
        raise ValueError('linked skills root')
    for directory in sorted((root / 'skills').iterdir()):
        if directory.is_symlink():
            raise ValueError(f'linked skill directory: {directory.name}')
        if not directory.is_dir():
            continue
        trigger = directory / 'evals' / 'trigger_eval_set.json'
        path = trigger if trigger.exists() else directory / 'evals' / 'evals.json'
        if not path.exists():
            continue
        if any(p.is_symlink() for p in (path, path.parent)):
            raise ValueError(f'linked query input: {path}')
        value = json.loads(path.read_text(encoding='utf-8'))
        kind = 'trigger positives' if path == trigger else 'eval prompt proxy'
        rows = value if path == trigger else value.get('evals') if isinstance(value, dict) else None
        if not isinstance(rows, list):
            raise ValueError(f'invalid query list: {path}')
        selected = []
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError(f'invalid query row: {path}')
            text = row.get('query' if path == trigger else 'prompt')
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f'invalid query text: {path}')
            if path == trigger and type(row.get('should_trigger')) is not bool:
                raise ValueError(f'invalid trigger label: {path}')
            if path != trigger or row['should_trigger']:
                selected.append(text)
        if selected:
            queries[directory.name] = list(dict.fromkeys(selected))
            sources[directory.name] = {'path': str(path.relative_to(root)), 'kind': kind}
    return queries, sources


def _execute(arguments, log, cwd):
    environment = {key: value for key, value in os.environ.items()
                   if key in {'PATH', 'SYSTEMROOT', 'WINDIR', 'TMPDIR', 'TMP', 'TEMP', 'LANG', 'LC_ALL'}}
    with log.open('w', encoding='utf-8') as output:
        return subprocess.run([sys.executable, '-I', '-m', 'dokimi', *arguments], cwd=cwd,
                              env=environment, stdout=output, stderr=subprocess.STDOUT).returncode


def _json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def scan(root, out, execute=_execute):
    root, out = root.resolve(), out.resolve()
    if not (root / 'skills').is_dir() or out.is_relative_to(root) or root.is_relative_to(out):
        raise ValueError('a skills checkout and an output directory outside it are required')
    out.mkdir(parents=True, exist_ok=False)
    checks, reports = {}, {}

    def check(name, arguments, artifact):
        code = execute(arguments, out / f'{name}.log', out)
        checks[name] = {'exit_code': code, 'status': 'pass' if code == 0 else 'fail'}
        try:
            report = _json(artifact)
            if not isinstance(report, dict):
                raise ValueError('expected a JSON object')
            required = {'scan': ('skills', 'tasks'), 'catalog': ('skills', 'status'),
                        'routing': ('field', 'result', 'n_candidates')}[name]
            if any(key not in report for key in required):
                raise ValueError('incomplete command report')
            reports[name] = report
        except (OSError, ValueError) as exc:
            checks[name] = {'exit_code': max(code, 2), 'status': 'fail', 'error': str(exc)}

    # catalog scan prints JSON to stdout, retained as the artifact as well as the log.
    check('scan', ['catalog', 'scan', '--root', str(root), '--kind', 'all', '--strict', '--format', 'json'],
          out / 'scan.log')
    if 'scan' in reports:
        (out / 'scan.json').write_text(json.dumps(reports['scan'], indent=2) + '\n', encoding='utf-8')
    check('catalog', ['catalog', 'eval', str(root), '--tier', 'static', '--out-dir', str(out / 'catalog')],
          out / 'catalog' / 'catalog.json')
    try:
        queries, sources = collect_queries(root)
        names = {row['name'] for row in reports.get('scan', {}).get('skills', [])}
        coverage = {'sources': sources, 'n_queries': sum(map(len, queries.values())),
                    'without_queries': sorted(names - queries.keys())}
        (out / 'query-coverage.json').write_text(json.dumps(coverage, indent=2) + '\n', encoding='utf-8')
        query_file = out / 'queries.json'
        query_file.write_text(json.dumps(queries, indent=2) + '\n', encoding='utf-8')
        if queries:
            check('routing', ['novelty', 'routing', '--all-vs-all', '--catalog', str(root),
                              '--queries-by-skill', str(query_file), '--out', str(out / 'routing.json')],
                  out / 'routing.json')
        else:
            checks['routing'] = {'exit_code': 0, 'status': 'skipped', 'reason': 'no existing labeled queries'}
    except (OSError, ValueError) as exc:
        checks['routing'] = {'exit_code': 2, 'status': 'fail', 'error': str(exc)}
        coverage = {'sources': {}, 'n_queries': 0, 'without_queries': []}
    skills = reports.get('scan', {}).get('skills', [])
    problems = reports.get('catalog', {}).get('problems')
    findings = (Counter(f"{problem['level']}: {problem['code']}" for problem in problems) if problems is not None
                else Counter(finding['code'] for skill in skills for finding in skill.get('findings', [])))
    lines = ['# Dokimi non-model scans', '', '| Check | Result |', '| --- | --- |']
    lines.extend(f"| {name} | {result['status']} |" for name, result in checks.items())
    lines += ['', f'Skills scanned: {len(skills)}. Existing queries: {coverage["n_queries"]}.',
              f'Skills with queries: {len(coverage["sources"])}; without queries: {len(coverage["without_queries"])}.',
              '', 'Routing is a lexical diagnostic, not model performance. Eval prompts are labeled as proxies.',
              '', 'JSON reports, query coverage and command logs are in the workflow artifact.', '']
    if findings:
        lines += ['| Skill diagnostic | Count |', '| --- | ---: |']
        lines.extend(f'| {code} | {count} |' for code, count in sorted(findings.items()))
    lexical = reports.get('routing', {}).get('result', {}).get('lexical', {})
    if lexical.get('own_rate'):
        lines += ['', '## Lexical routing (advisory)', '',
                  '| Skill | Scored queries | Own-selection share | Query source |', '| --- | ---: | ---: | --- |']
        for name, rate in sorted(lexical['own_rate'].items()):
            label = html.escape(name).replace('|', '&#124;').replace('`', '&#96;').replace('\n', ' ')
            lines.append(f"| {label} | {lexical['n_scored'][name]} | {rate:.4f} | {coverage['sources'][name]['kind']} |")
    (out / 'summary.json').write_text(json.dumps(checks, indent=2) + '\n', encoding='utf-8')
    (out / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return max(result['exit_code'] for result in checks.values())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    try:
        raise SystemExit(scan(args.root, args.out))
    except (OSError, ValueError) as error:
        parser.exit(2, f'{error}\n')
