<!--
Copyright (C) 2026 Intel Corporation
SPDX-License-Identifier: Apache-2.0
-->

# Dokimi CI

Pull requests run credential-free catalog and evaluation-definition checks for
this repository. The existing Harbor workflow handles executable task oracles.

Model evaluation, baseline recording and revalidation are separate manual
workflows. Select the catalog subject, answer and judge models/providers,
repetitions and applicable budget at dispatch. No model, provider, benchmark
threshold or task subset is selected by this integration.

Before enabling model runs, maintainers configure these repository variables:

| Variable | Purpose |
| --- | --- |
| `DOKIMI_ENVIRONMENT` | Protected environment approving model execution |
| `DOKIMI_POLICY` | Relative path to the reviewed policy file in the approved content revision |
| `DOKIMI_POLICY_DIGEST` | Canonical policy digest used to verify published and recorded evidence |

The pinned engine defines the supported providers, credential names and policy
schema. Provision the optional secrets referenced by the callers for the selected
providers; only matching credential bindings are forwarded. API runs
require a monetary budget; subscription runs require a call limit. Missing
credentials or policy cannot qualify a baseline.

The approved base supplies the primary evaluation suite. Results are
informational and do not change catalog status. Recording additionally requires
the measured pull request to be merged and a passing, matching receipt. It writes
signed-off records to `dokimi-baselines` using compare-and-swap. Revalidation
measures the recorded subject again without updating that baseline.

Workflow references and the interface snapshot under `tools/tests/fixtures/`
pin the measuring instrument. Update them together when upgrading Dokimi.
