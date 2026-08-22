# GitHub Actions Runbook

Operational how-to for [`docs/standards/GITHUB_ACTIONS_STANDARD.md`](../standards/GITHUB_ACTIONS_STANDARD.md).
Read the standard first — this runbook is the "how", the standard is the "what and why".

## 1. Check current billing

```bash
gh api "/users/surencio/settings/billing/usage?year=2026&month=8"
```

- `year`/`month` select the cycle; the endpoint returns the account's usage-based billing for that
  month, including a per-item breakdown you can filter to Actions/Linux-minute line items.
- There is no per-repo breakdown in the raw response — repo attribution (the Pareto in the cost-baseline
  record) came from cross-referencing the billing period against `gh run list -R <repo> --created
  >=<cycle-start>` per governed repo and summing billed minutes. That is manual today; automating it is
  a Phase 2 candidate, not something this runbook claims exists yet.
- Run this **before** assuming a spend spike is a specific repo's fault — check the total first, then
  narrow.

## 2. Audit a repo's workflows against the standard

There is no CI gate that lints a consuming repo's workflow YAML against
[`GITHUB_ACTIONS_STANDARD.md`](../standards/GITHUB_ACTIONS_STANDARD.md) §2 today (stated explicitly in
the standard's §5 — this is a real gap, not an oversight). Until that exists, audit manually:

```bash
# 1. Every job has a bounded timeout-minutes (§2.1)
gh api "repos/<owner>/<repo>/contents/.github/workflows" --jq '.[].name' | \
  while read -r wf; do
    echo "== $wf =="
    gh api "repos/<owner>/<repo>/contents/.github/workflows/$wf" --jq '.content' | base64 -d | \
      grep -n '^\s*runs-on:\|^\s*timeout-minutes:' || true
  done
# every runs-on: line should have a timeout-minutes: line in the same job block.

# 2. Concurrency cancellation is scoped correctly (§2.2)
grep -n "cancel-in-progress" .github/workflows/*.yml
# confirm each hit is on a workflow triggered by pull_request/push-to-PR-branch,
# never on a schedule- or post-merge-audit-triggered workflow.

# 3. npm install hardening on PR-head-triggered jobs (§2.4)
grep -n "npm install" .github/workflows/*.yml
# every hit inside a job with `on: pull_request` (or checking out PR-head refs)
# should read `npm install --ignore-scripts`.
```

For the account-wide **completeness** view (does a repo even carry the enrollment marker and reference
the standard) rather than a per-workflow content audit, run
[`scripts/check_actions_governance_enrollment.py`](../../scripts/check_actions_governance_enrollment.py)
(see §4 below) — the two are complementary, neither substitutes for the other.

## 3. When a job hangs

Worked example — the real incident this standard exists to prevent, described in
[`GITHUB_ACTIONS_COST_BASELINE_2026-08.md`](../experiments/GITHUB_ACTIONS_COST_BASELINE_2026-08.md):

1. **Confirm it's actually hung, not just slow.** `gh run view <run-id> -R <owner>/<repo>` shows the
   in-progress step. If a step has been running far longer than any clean historical run of that same
   step, treat it as hung rather than waiting it out — GitHub will not kill it early on your behalf.
2. **Cancel it now.** `gh run cancel <run-id> -R <owner>/<repo>`. Every minute it keeps running bills.
   Don't wait for the 6-hour ceiling to do this for you.
3. **Check whether it's a real regression or a transient stall.** In the incident that motivated this
   runbook, the hang was an `apt-get install shellcheck` step stalling after fetching Ubuntu archive
   package indexes — sibling repos ran the identical step cleanly seconds apart, so this read as a
   transient GitHub-hosted-runner/mirror stall, not a permanent code bug. Re-running the workflow (`gh
   run rerun <run-id>`) is a reasonable first move once a timeout is in place to bound the retry.
4. **Add (or fix) `timeout-minutes` on the job, immediately, in the same PR/commit that addresses the
   hang.** Do not treat "it was transient" as a reason to skip this — a transient stall recurs, and
   without a timeout the next occurrence bills the full 6 hours again. See
   [`GITHUB_ACTIONS_STANDARD.md` §2.1](../standards/GITHUB_ACTIONS_STANDARD.md#21-every-hosted-runner-job-sets-a-bounded-timeout-minutes)
   for the values in use elsewhere in the account.
5. **Record it.** If the repo has a cost ledger or incident log (this repo's
   [`docs/experiments/GOVERNANCE_COST_LEDGER.md`](../experiments/GOVERNANCE_COST_LEDGER.md) pattern, or a
   per-customer-repo equivalent), log the incident, the billed-minute cost, and the fix. Recurring
   incidents that never get logged never accumulate into a fixable pattern — that is exactly how the two
   6-hour hangs measured in the same billing cycle went unnoticed until the account-wide billing review.

## 4. Enrolling a repo in this standard

This standard propagates through the same mechanism every other platform standard does — the
`PLATFORM_VERSION` pin and its `docs/UPSTREAM/` snapshot, documented in
[`VERSIONING.md`](../../VERSIONING.md). Nothing new is invented here.

**To enroll a repo that has never joined the platform-pin mechanism**, first confirm it belongs in scope
at all: [`governance/repo_scope_registry.json`](../../governance/repo_scope_registry.json) classifies
every repo the account owns as `governed` / `archived` / `intentionally_unmanaged` / `unclassified`. Only
a `governed`-class entry (without `needs_onboarding: true`) is a candidate for the steps below. A repo the
live account has but this registry has never heard of surfaces as `unclassified` the moment anyone runs
`--scope` (see below) — that is the signal to add a registry entry, with a `reason` if it turns out to be
out of scope, before enrolling it.

1. Add a `PLATFORM_VERSION` file at the repo root, pinning the current platform tag (`git describe
   --tags` in `ryzalab-platform`, or `gh api repos/surencio/ryzalab-platform/tags --jq '.[0].name'`).
2. Add a `profile:` line declaring the repo's kind. See
   [`VERSIONING.md` § Repo-profile marker](../../VERSIONING.md#repo-profile-marker-profile-line) for the
   two profiles defined so far (`customer-ha`, `platform-consumer`) and which one fits. This must match
   the `profile` already recorded for the repo in `repo_scope_registry.json` — the enrollment audit hard-
   FAILs a `profile:` value outside the recognized set (a typo, e.g. `costomer-ha`), it never silently
   accepts or passes one through.
3. Set up `docs/UPSTREAM/` per the repo's profile — the two profiles export **different amounts** of the
   platform tree, and the difference is the point, not an implementation detail:
   - **`customer-ha`** (`ryzalab-austin-main`, `ryza-willr-main`, `ryzalab-par-main`, and eventually
     `ryzalab-003-thirdeye` once it's onboarded): full mirror of the pinned platform tree, unchanged from
     today's behavior. Manifest: [`bootstrap/export-manifests/customer-ha.txt`](../../bootstrap/export-manifests/customer-ha.txt)
     (currently `**` — everything). A customer-ha site needs the whole apparatus: HA standards,
     commissioning, device classification, access management, the scaffolder, all of it.
   - **`platform-consumer`** (`ryzalab-website`, `ryzalab-notion-mcp`, `agent-skills`,
     `ryzalab-email-scraper`, `ryzalab-automation`, `ryzalab-tax-project`, `ryzalab-public`, `leakprint`):
     a narrowed mirror driven by
     [`bootstrap/export-manifests/platform-consumer.txt`](../../bootstrap/export-manifests/platform-consumer.txt)
     — `docs/standards/`, this runbook, and `VERSIONING.md` only. It explicitly excludes `tests/`,
     `tools/agentops/tests/`, and platform-only dev/ops surface (`scripts/`, `tools/`, `agent-config/`,
     `governance/`, `bootstrap/`, and every other `docs/` subtree). This narrowing exists because the full
     mirror caused four real incidents in consumer repos that have no use for platform's own dev
     apparatus: a brand-voice checker tripping on mirrored docs (fixed with a repo-local exclusion, not by
     narrowing the mirror), `ryzalab-automation`'s pytest auto-collecting `docs/UPSTREAM/tests/` and
     hard-failing on a missing dependency, `ryzalab-tax-project`'s `ruff` linting the mirrored Python tree
     (287 errors), and `ryzalab-public`/`leakprint` both getting rejected by GitHub push protection on a
     synthetic secret-shaped test fixture living under `docs/UPSTREAM/tools/agentops/tests/test_secrets.py`.
     Copy only the manifest's paths — do not run a general-purpose mirror script against this profile.
     `bootstrap/scaffold-repo.sh --profile platform-consumer` produces this automatically for a fresh repo;
     see its `--help` for the manual-copy equivalent when retrofitting an existing one.
4. Open the enrollment as a normal PR in the consuming repo, per the customer-pin contract in
   `VERSIONING.md`.

**To stay current** once enrolled: follow the same PATCH/MINOR/MAJOR pin-bump discipline
`VERSIONING.md` already defines for every other platform standard. A MINOR bump that only adds to
`GITHUB_ACTIONS_STANDARD.md` (a new rule, an additional "what NOT to do" case) is a routine pin-bump PR;
a MAJOR bump (a rule changing from advisory to mandatory in a way that requires a specific workflow
edit) needs the migration steps from the platform's `MIGRATION_*.md` for that change, same as any other
breaking bump. A `platform-consumer` repo only needs to re-copy the manifest's paths on a bump, never the
full tree.

**To check enrollment status account-wide**, run
[`scripts/check_actions_governance_enrollment.py`](../../scripts/check_actions_governance_enrollment.py).
Repos are discovered live and scored against `repo_scope_registry.json` — there is no hardcoded repo list
to keep in sync by hand:

```bash
python3 scripts/check_actions_governance_enrollment.py            # discover + score every governed repo
python3 scripts/check_actions_governance_enrollment.py --scope     # classification only, no scoring
python3 scripts/check_actions_governance_enrollment.py --repo surencio/ryzalab-website --json
```

Read the script's own docstring before trusting its output — it states plainly what it does and does
not check (marker presence, standard-doc reference, and pin currency — i.e. `enrollment_status` — never
workflow-YAML content). **Enrollment and workflow compliance are two separate metrics from two separate
tools and must never be reported as one number.** Whether a repo's actual `.github/workflows/*.yml`
follows this standard's rules (§2.1–§2.4) is `WORKFLOW_COMPLIANCE_STATUS`, computed by the advisory,
read-only [`scripts/check_actions_workflow_compliance.py`](../../scripts/check_actions_workflow_compliance.py) —
not a required check, and not folded into `enrollment_status` under any circumstance. A repo can be
enrollment-PASS and compliance-FAIL, or the reverse.
