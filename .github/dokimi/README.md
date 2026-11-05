<!--
Copyright (C) 2026 Intel Corporation
SPDX-License-Identifier: Apache-2.0
-->

# Dokimi non-model scans

CI installs a pinned upstream `intel/dokimi` revision and runs:

- Catalog preflight: skill format, broken or escaping links, duplicates,
  description diagnostics, and declared task availability.
- Static catalog evaluation: manifest, suite, ownership and eval consistency,
  with versioned JSON and Markdown reports.
- Lexical routing: existing positive trigger queries, or existing eval prompts
  labeled as proxies, compete against the catalog. Missing query coverage is
  reported; no queries are generated from skill text.

The workflow summary shows check results, query coverage and diagnostic counts.
Download its artifact for complete findings, per-skill reports and command logs.
Structural errors fail CI. Lexical scores are advisory and have no quality gate.
These scans need no credentials, model, provider or repository variables. They
execute no skill scripts, code examples, task solutions or Docker workloads, and
do not establish skill efficacy or change catalog status.
