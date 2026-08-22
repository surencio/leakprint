# Standard — GitHub Actions Governance

**Status:** ACTIVE v1.0 (codifies controls already shipped across the account; see §6)
**Risk Tier:** Standard content changes follow the normal PR risk-tier classification in
[`governance/agent_control_plane_policy.json`](../../governance/agent_control_plane_policy.json) —
this document does not define its own review process, and nothing below should be read as doing so.
**Program alignment:** [`docs/experiments/GITHUB_ACTIONS_COST_BASELINE_2026-08.md`](../experiments/GITHUB_ACTIONS_COST_BASELINE_2026-08.md)
(the evidence this standard is built from) and [`VERSIONING.md`](../../VERSIONING.md) (how this
standard reaches customer/consumer repos).

> Claim-maturity tags: **[MEASURED]** = observed on the live account; **[TARGET]** = acceptance bar.

## 1. Why this exists

A billing review of the `surencio` GitHub account (cycle 2026-08-01–19) measured **$10.00 net billed**
against a 3,000-min/mo included allowance that was exhausted mid-day 2026-08-14, driven overwhelmingly
by two incidents: a `governance-audit` job in `ryzalab-website`'s `validate-pr.yml` and a `lint` job in
`ryza-willr-main`'s `ci.yml` each ran for **exactly 6 hours** — GitHub's default per-job ceiling —
because neither had a `timeout-minutes` set. Together those two runs were **720 runner-minutes / $4.32
gross** [MEASURED], the majority of the cycle's measured spend. Full baseline, Pareto, and root-cause
detail live in the cost-baseline record cited above; this standard exists to make sure it does not
recur, in this repo or any repo that consumes it.

This standard governs **what a GitHub Actions workflow must do**, repo-wide. It does not govern who is
allowed to approve, merge, or authorize a change — that is
[`agent_control_plane_policy.json`](../../governance/agent_control_plane_policy.json)'s domain, and
this document defers to it entirely rather than restating any of it.

## 2. The rules (mandatory)

### 2.1 Every hosted-runner job sets a bounded `timeout-minutes`

**Non-negotiable.** GitHub's default job ceiling is 6 hours (360 minutes) on a `GITHUB_TOKEN`-authenticated
job. A job with no `timeout-minutes` inherits that ceiling, and a stall — a hung install step, a
flaky network mirror, a test that never returns — runs the full 6 hours before GitHub kills it. That is
exactly what happened twice in the same billing cycle [MEASURED], and it is the single largest
preventable cost driver this account has measured.

- Every job in every workflow sets an explicit `timeout-minutes`.
- Values in use across the account: **10–15 min** for typical lint/validate/lightweight jobs, **30 min**
  for a job installing Playwright browsers. `ubuntu-slim`'s job-timeout ceiling is 15 min, noted here for
  reference only — no repo runs `ubuntu-slim` today, so this is not yet a live constraint.
- Pick a number that comfortably covers the slowest clean run you have actually observed, not the
  fastest. A timeout that fires on a normal run just adds flaky-red noise, which erodes trust in the
  gate faster than the cost problem it was meant to solve.

### 2.2 Concurrency cancellation is scoped to PR-triggered runs only

`concurrency: { group: ..., cancel-in-progress: true }` is a real cost win — sampling on `lint.yml`
showed **79% of PR-triggered runs were for a branch head later superseded by a newer push**, i.e. wasted
runner-minutes for a result nobody would ever read [MEASURED]. But cancellation is only safe when the
run's *entire point* is to describe the current head, and nothing is lost by describing an old head
never at all.

- **Apply `cancel-in-progress` only to workflows triggered by `pull_request` (or `push` to a PR branch)**.
  A group key built from the ref alone (e.g. `group: ${{ github.workflow }}-${{ github.ref }}`) is
  **not sufficient by itself** the moment the same workflow file also triggers on `push` to `main`:
  `github.ref` is `refs/heads/main` on every push to `main`, so successive post-merge runs would share
  that same group and a later one would cancel an earlier one — exactly the "missing audit record"
  failure this section warns against two paragraphs below, not a hypothetical. Include `github.event_name`
  in the group key, and gate `cancel-in-progress` on the event being `pull_request`, e.g.:

  ```yaml
  concurrency:
    group: ${{ github.workflow }}-${{ github.event_name }}-${{ github.event.pull_request.number || github.sha }}
    cancel-in-progress: ${{ github.event_name == 'pull_request' }}
  ```

  This is the exact pattern shipped in `lint.yml`/`agentops-tests.yml` (`ryzalab-platform` PR #203) — see
  §6 for the evidence trail. Push-triggered runs land in a different group (by `event_name`) and never
  get `cancel-in-progress: true` regardless, so two safety mechanisms cover the same failure mode, not one.
- **Never** apply it to:
  - post-merge or audit workflows (e.g. a `qa-gate-postmerge-audit`-style job) — these exist to produce
    evidence about a merge that already happened, and a cancelled run is a missing audit record, not a
    saved minute.
  - scheduled workflows (`on: schedule`) — a cancelled scheduled run is a silently skipped check, and
    nothing else will notice it didn't happen.
  - any workflow whose completion is itself the governance evidence (digest generators, staleness
    audits, and anything in that family).
- If a workflow serves both purposes (e.g. one file handles both `pull_request` and `schedule`
  triggers), scope the concurrency group so it only ever cancels the `pull_request`-triggered run —
  never let a scheduled or post-merge trigger share a cancellable group with a PR trigger. The
  `event_name`-in-group-key pattern above is how: a scheduled or post-merge trigger's `event_name` never
  equals `pull_request`, so it can never land in a group whose `cancel-in-progress` is true.

### 2.3 Consolidate jobs by shared toolchain, not blindly

GitHub bills each hosted job a **minimum of 1 rounded-up minute**, regardless of real duration. Eight
one-job-per-check workflows doing 1.7 minutes of combined real work still bill 8 minutes. Consolidating
into fewer jobs is a legitimate cost lever, but the axis that matters is **toolchain**, not "fewer jobs
at any cost":

- Group checks that already share a runner setup (same `actions/setup-node`, same `npm install`, same
  Python venv) into one job. A `shellcheck`-only job that needs `apt-get install shellcheck` and nothing
  else stays separate — folding an apt-based toolchain into a node-based one buys nothing and couples two
  unrelated failure surfaces.
- **Preserve step-level failure attribution.** Consolidating checks into one job must not collapse them
  into a single opaque step — each check keeps its own named step (or its own `make <target>`, per this
  repo's own `validate` job pattern) so a failure still names *which* check failed, not just "the job
  failed."
- Don't consolidate a check that legitimately needs isolation (a different permission scope, a different
  timeout profile, a step that installs untrusted PR-supplied code) purely to save a billed minute. The
  1-minute floor is real, but it is the cheapest thing this standard asks you to trade away.

### 2.4 Lockfile/lifecycle-script hardening on every PR-head-triggered job

Any job that runs on a `pull_request` trigger executes code from the PR head **before** any gate in that
job has had a chance to reject it. An unmodified `npm install` runs `package.json`'s
`preinstall`/`postinstall` scripts unconditionally — a PR that smuggles a malicious lifecycle script gets
it executed on the runner ahead of every check the workflow was written to run.

- Any job triggered by `pull_request` (or otherwise checking out PR-head code before review) that runs
  `npm install` runs `npm install --ignore-scripts` instead — this unconditionally blocks every
  `preinstall`/`postinstall` script for every installed package, named or transitive.
- pip has the same class of hazard but no single equivalent flag: `--no-deps` only narrows which
  packages get installed (fewer chances for a malicious build hook to run), it does **not** stop an
  explicitly-named package's own `setup.py`/build backend from executing. The closer structural
  equivalent is `pip install --only-binary=:all:` against a pinned, hash-checked requirements file —
  wheels don't execute arbitrary build-time code the way source distributions can.
- **Known current gap, not fixed by this pass**: `ryzalab-platform`'s own `lint.yml` (`validate` and
  `python-checks` jobs) runs `pip install pyyaml==6.0.3` / `pip install yamllint==1.35.1` on
  `pull_request`-triggered code today with none of this hardening — the npm job in the same file got
  `--ignore-scripts` in PR #203, the pip installs did not. This standard names the gap rather than
  silently implying it's already closed; closing it means editing `lint.yml`, which this
  documentation-only pass deliberately does not do (see §4).
- This is a security control that happens to also be free — it does not change billed minutes — but it
  belongs in this standard because it is enforced at the exact same trigger boundary (`pull_request`,
  PR-head code) that every other rule here reasons about.

## 3. What NOT to do

These are the real cost drivers this account has actually measured, not hypothetical ones. Listing the
negative case matters as much as the positive rules above, since a well-intentioned change can reproduce
one of these without ever violating §2's letter:

- **Superseded-head waste** — running a full workflow against a commit that a newer push on the same PR
  already obsoleted. This is what §2.2 exists to close; the fix is scoping cancellation correctly, not
  just adding a `concurrency:` block anywhere convenient.
- **Sub-minute job-count multiplication** — splitting fast checks into many small jobs "for clarity" when
  each one bills a full minute floor regardless of real duration. §2.3 is the corrective, but the trap is
  easy to reintroduce one small PR at a time.
- **Duplicate PR + push runs** — a workflow triggered on both `pull_request` and `push` for the same
  branch produces two runs of the same work for the same commit unless the triggers are deliberately
  scoped apart (e.g. `push` limited to `main`/release branches, `pull_request` covering everything else).
  Check `on:` triggers for accidental overlap before assuming a new workflow is cheap.
- **Repeated paid AI review on intermediate heads** — a bot/agent review step (cross-family QA, an AI
  code-review action) that reruns on every push to a PR, including pushes that are mid-flight and not
  ready for review, burns paid review capacity on heads nobody will read the review of. Scope AI-review
  triggers the same way §2.2 scopes cancellation: to the head that will actually be evaluated, not every
  intermediate one.

## 4. What this standard does not cover

- **Identity, evidence roles, authorization, and risk-tier classification** — entirely
  [`agent_control_plane_policy.json`](../../governance/agent_control_plane_policy.json)'s domain. This
  standard is only about what a workflow *does* on the runner, never about who is allowed to approve
  what.
- **Workflow YAML rewrites in any specific repo.** This document is the ruleset; applying it to a given
  repo's `.github/workflows/*.yml` is separate, repo-scoped work, tracked and executed independently of
  this standard landing.
- **Repo enrollment mechanics** — how a repo declares which profile it is and which version of this
  standard it is enrolled in is the `PLATFORM_VERSION` profile marker, documented in
  [`VERSIONING.md` § Repo-profile marker](../../VERSIONING.md#repo-profile-marker-profile-line) and
  operationalized in [`docs/runbooks/GITHUB_ACTIONS_RUNBOOK.md`](../runbooks/GITHUB_ACTIONS_RUNBOOK.md).

## 5. Enforcement

There is no CI gate today that checks a *consuming* repo's workflow YAML against this standard — that
would require reading into every governed repo's `.github/workflows/`, which is out of scope for this
revision. What exists:

- [`scripts/check_actions_governance_enrollment.py`](../../scripts/check_actions_governance_enrollment.py) —
  a read-only, account-wide **completeness** audit: does a governed repo carry the profile marker, does
  it reference this standard (directly or via its pinned `docs/UPSTREAM/` snapshot), and is its enrolled
  version current. It does **not** parse or lint the repo's actual workflow YAML against §2 — that is a
  Phase 2 gap, stated honestly rather than silently assumed away.
- This repo's own `.github/workflows/lint.yml` and `Makefile` (`validate-ci-parity`, job consolidation,
  scoped concurrency) already follow §2.1–§2.3 as of `ryzalab-platform` PR #203
  (`c5a5b708bb78d3531786050c11da07e534248ca1`) — see §6 for the evidence trail. §2.4 is a known
  exception here: its `npm install --ignore-scripts` half landed, its pip half did not (see §2.4).

## 6. Evidence trail

| Fix | Repo | PR | Rule |
|---|---|---|---|
| `timeout-minutes` added to every previously-unbounded job | `ryzalab-website` | #97 | §2.1 |
| `timeout-minutes` added to every previously-unbounded job | `ryza-willr-main` | #32 | §2.1 |
| `timeout-minutes` added to every previously-unbounded job | `ryzalab-par-main` | #51 | §2.1 |
| `timeout-minutes` added to every previously-unbounded job | `ryzalab-austin-main` | #230 | §2.1 |
| 8→4 job consolidation by shared toolchain; scoped `cancel-in-progress`; `npm install --ignore-scripts` | `ryzalab-platform` | #203 (`c5a5b708bb78d3531786050c11da07e534248ca1`) | §2.2, §2.3, §2.4 |

Full method, timestamps, and the Pareto behind these numbers:
[`docs/experiments/GITHUB_ACTIONS_COST_BASELINE_2026-08.md`](../experiments/GITHUB_ACTIONS_COST_BASELINE_2026-08.md).

## Revision history

| Date | Version | Note |
|---|---|---|
| 2026-08-20 | ACTIVE v1.0 | Initial standard, codifying controls already shipped across five repos (see §6) rather than proposing new ones. |
| 2026-08-21 | v1.0, patch (platform v0.5.1) | §2.2's illustrative group-key example (`group: workflow-ref`) was unsafe for a workflow that also triggers on `push` to `main` — successive post-merge runs would share a group and cancel each other, contradicting the section's own "never cancel post-merge evidence" rule two paragraphs below. Corrected to the actual shipped pattern (`event_name` in the group key, `cancel-in-progress` gated on `pull_request`). No rule changed, no customer-side action required — this is a documentation-accuracy patch, not a MINOR/MAJOR change. |
