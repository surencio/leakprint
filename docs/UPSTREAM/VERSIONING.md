# Versioning policy

`ryzalab-platform` uses semver (`MAJOR.MINOR.PATCH`). Customer repos pin a specific tag in their `PLATFORM_VERSION` file. Pin bumps are deliberate PRs in customer repos.

## Version increments

| Increment | When | Customer impact |
|---|---|---|
| **PATCH** (`v0.1.0` → `v0.1.1`) | Typo fixes, link corrections, prose clarifications, non-substantive edits. No change to standards content. | Auto-consumed if customer repo policy is "track latest patch in pinned minor." Most customers should opt into this. |
| **MINOR** (`v0.1.0` → `v0.2.0`) | New standard added, new optional template, new runbook, new PRD, scaffolder enhancement, additive change to existing standard (e.g., new tripwire condition added). Existing customer compliance is unaffected. | Pin bump is a deliberate PR in each customer repo. CI validates the new platform docs render correctly in `docs/UPSTREAM/`. |
| **MAJOR** (`v0.x.y` → `v1.0.0`) | Breaking change: a standard's mandatory rule changes in a way that requires customer-side action; a runbook's command syntax changes; a template's required fields change; a Gate-2 commissioning row is added that requires existing customers to backfill. | Pin bump requires planned migration. Each customer's PR includes the migration steps from the platform's `MIGRATION_*.md` for that breaking change. |

## What counts as a breaking change

Any of the following triggers a MAJOR bump:

- A new mandatory commissioning row in `ACCESS_MANAGEMENT_STANDARD.md §11` that existing customers must backfill.
- A change to the `[SITE]-[room]-[node]-[type]` entity naming pattern in `VALIDATION.md`.
- Removal or renaming of a runbook that customer repos cite by path.
- A change to `bootstrap/scaffold-customer.sh` interface (flag rename, removed flag).
- A change to the `agent-config/CLAUDE.md` C1–C7 SSRP rules that requires customer agents to update behavior.
- Removal of a `docs/templates/` template that customer repos consume.

Any of the following triggers a MINOR bump (additive, non-breaking):

- New standard, runbook, template, PRD, ADR added.
- New optional field added to a template (existing fills still validate).
- New tripwire condition added to an existing standard.
- New scaffolder flag (existing flag set still works).
- Performance/resilience improvement that doesn't change customer-side behavior.

PATCH bumps cover prose, typos, link corrections, formatting, and non-substantive edits.

## Customer-pin contract

Each customer repo's `PLATFORM_VERSION` file is a single line, e.g.:

```
v0.1.0
```

Optional second line for patch-tracking policy:

```
v0.1.0
track-patches: true
```

When `track-patches: true`:
- Customer CI auto-bumps `PLATFORM_VERSION` to the latest patch in the pinned minor (e.g., `v0.1.0` → `v0.1.3`) on platform release.
- The customer repo's `docs/UPSTREAM/` snapshot is refreshed automatically.
- A "patch bump" PR is opened and auto-merged after CI green if the diff is patch-only.

When `track-patches: false` (default for customers wanting strict pinning):
- Every bump requires a manual PR.

Major and minor bumps **always** require a manual PR regardless of `track-patches`.

### Repo-profile marker (`profile:` line)

`PLATFORM_VERSION` also carries an optional `profile:` line declaring **what kind of repo this is**,
for CI/Actions-standard purposes. This is a completely different axis from
[`agent_control_plane_policy.json`](governance/agent_control_plane_policy.json)'s identity/evidence-
role/authorization/risk-tier domain — it never determines who can approve or merge anything, only which
platform standards a repo is expected to have enrolled in.

```
v0.4.0
track-patches: false
profile: customer-ha
```

Rules:

- **Lines 2+ are unordered `key: value` pairs.** A file with only a `track-patches:` line, only a
  `profile:` line, both, or neither (bare version, line 1 only) are all valid — this keeps the format
  backward-compatible with every `PLATFORM_VERSION` file that predates the `profile:` line.
- **`profile` values defined so far:**
  - `customer-ha` — a live customer Home Assistant site repo (the existing shape:
    `ryzalab-austin-main`, `ryza-willr-main`, `ryzalab-par-main`). Carries the full customer-repo
    governance surface: `ACCESS_MANAGEMENT_STANDARD.md`, `HA_RELEASE_GATE_STANDARD.md`,
    `CUSTOMER_REPO_BOOT_SEQUENCE.md`, and everything else scoped to a live HA install.
  - `platform-consumer` — a governed repo that consumes platform-level standards (this one included:
    [`GITHUB_ACTIONS_STANDARD.md`](docs/standards/GITHUB_ACTIONS_STANDARD.md) is the first standard a
    `platform-consumer` repo is expected to enroll in) but is **not** a customer HA site — no live
    device access, no commissioning gates, no `ACCESS_MANAGEMENT_STANDARD.md §11` rows. `ryzalab-website`
    and `ryzalab-automation` are the account's current candidates for this profile; neither has enrolled
    yet (see [`docs/runbooks/GITHUB_ACTIONS_RUNBOOK.md` §4](docs/runbooks/GITHUB_ACTIONS_RUNBOOK.md)).
    Named `platform-consumer` rather than `governed-service` because the defining trait is *which
    platform surface applies*, not whether the repo runs a service — a static site and a scripts-only
    repo are both `platform-consumer` even though neither is "a service" in the usual sense.
  - Additional profiles are added the same way any other additive template field is (a MINOR bump, per
    the increment table above) — this list is expected to grow, not to be exhaustive today.
- **A repo without a `profile:` line is unclassified**, not defaulted to either value. Tooling that
  reads this field (e.g. `scripts/check_actions_governance_enrollment.py`) must treat a missing
  `profile:` as "not yet declared," never silently assume `customer-ha` because that happens to be every
  repo that has one today.
- Adding the `profile:` line to an existing `PLATFORM_VERSION` file, or adding a new `profile` value, is
  a MINOR change under the increment table above (new optional field; existing fills without it still
  validate).

## Release flow

1. PR merges to `main` in this repo.
2. Operator decides increment (patch/minor/major) based on this policy.
3. `git tag vX.Y.Z` and `gh release create vX.Y.Z --notes "..."` — release notes describe what changed and the customer-side action required (if any).
4. Notion: Work Log entry tagged `platform-release`.
5. Customer repos receive a notification (manual or via webhook in v1.x) and open pin-bump PRs as appropriate.

## Pre-1.0 stability

Until `v1.0.0`, the API surface is unstable and minor bumps may include changes that elsewhere would be major. Customer repos pinning pre-1.0 versions should treat every minor bump as requiring a manual review of the diff. The `v1.0.0` cut happens when:

- All existing customer repos consume platform via pin.
- The scaffolder produces a customer repo that is structurally identical to a hand-built one.
- Multi-agent governance has been validated end-to-end (Cursor + Claude + Codex + Gemini all read the same SSOT).
- The migration plan in `MIGRATION_PLAN.md` has been executed and that doc moves to historical record.

After `v1.0.0`, customer pin-bumps for minor versions become routine; only major bumps require migration work.

## Tag retention

All tags retained indefinitely. Customer repos can pin to any historical tag without fear of removal. Tags are immutable — a release that needs correction gets a new patch bump rather than a re-tag.
