<!--
Copyright (C) 2026 Intel Corporation
SPDX-License-Identifier: Apache-2.0
-->

# Dokimi consumer configuration

Pull requests run the reusable Dokimi catalog checks without credentials. The
`dpnp-oracles` job also builds and executes all five dpnp oracle/verifier pairs on
an Ubuntu x86 runner. Its JSON receipts and build/verifier logs are retained as
artifacts. Passing static checks establishes catalog integrity; passing oracles
establishes task solvability. Neither establishes that a skill improves answers.

The manual model job uses the `claude-cli` subscription transport for both the
answerer and a different judge model. It does not accept API keys. Select one
`skill/<name>`, full Claude model IDs, exact pull request head/base commits, and an
explicit maximum call count. Every answer and judge invocation consumes that
count. Billed USD remains unknown (`null`); the Claude CLI's list-price estimate
is not reported as subscription spend.

Local use can reuse an existing Claude Code subscription login. Hosted use needs
a protected `dokimi-live` environment and an explicitly configured
`DOKIMI_CLAUDE_CODE_OAUTH_TOKEN` secret. No token is supplied by these files. Missing
subscription authentication fails before model calls. The model controller runs
only from the repository's approved default branch, so adding these files in a
pull request does not immediately authorize hosted model execution.

For existing skills, the base revision supplies every primary evaluation case,
expected answer, assertion, and executable-task verifier. The model receives no
skill, the approved skill, or the candidate skill over that same suite. Head-added
cases are inventoried but not executed by the CI gate; approve and revalidate the
suite separately. Imported skills
marked `evaluated_here: false` receive checks only. A missing supported suite is
reported as `no_tasks` rather than receiving a runtime pass.

`policy.yaml` requires at least three independent tasks, bounds per-task
regression, and requires evidence of positive improvement. Repetitions do not
increase the independent task count. These checks do not change `skills.yaml`
status or award `validated`. A separate publisher verifies the source run,
artifact, current pull request commits, and trusted policy before posting an
informational receipt; it does not check out candidate code.

The workflow and action references are pinned to the fork's implementation
commit. Updating the measuring instrument requires deliberately updating those
pins. The five dpnp images pin `dpctl==0.22.1` alongside `dpnp==0.20.0` because
[dpctl 0.23.0 removed the Cython program API](https://github.com/IntelPython/dpctl/releases/tag/0.23.0)
used by the existing dpnp wheel. Float64 task requirements and verifiers remain
unchanged; an amd64 emulator without native float64 is not a qualifying host.

## Manual baseline lifecycle

After these workflows are approved and merged into the fork's default branch,
`Record approved Dokimi baseline` can record a qualified model evaluation. Supply
the exact source run ID and attempt, the approved controller commit that produced
it, and the expected current baseline record digest (`none` for the first record).
The reusable engine requires the evaluated pull request to be merged, authenticates
the source artifact and policy, checks the merged content identity, and requires a
qualified behavioral pass. A static pass, failed or incomplete evaluation, or an
unqualified subscription pilot cannot be recorded as a passing baseline.

Recording is a separate manual action. Only its job receives `contents: write`,
and the engine writes compare-and-swap records to `dokimi-baselines` with
`vchamarthi`'s configured DCO identity. The configuration declares that branch as
the store; declaring it does not create it or authorize an automatic update.
Neither recording nor any other caller changes the default branch.

`Revalidate Dokimi baseline` is also manual. Select a baseline JSON path on
`dokimi-baselines`, an exact approved content revision, the matching subject, full
answer and independent judge model IDs, repetitions, and a finite call cap. It uses
only the existing Claude subscription secret reference, runs behind `dokimi-live`,
and preserves billed USD as unknown. Its report is a new measurement; the workflow
has read-only repository access and does not promote or replace a baseline. There
is no schedule and no automatic promotion.

`tools/tests/fixtures/dokimi-workflow-contracts.json` captures the actual
`workflow_call` input and secret interfaces from the pinned framework commit,
including source-file digests. The consumer tests reject missing or unknown call
inputs and pin drift. Refresh that snapshot from the actual engine interfaces
when deliberately updating the framework pin.
