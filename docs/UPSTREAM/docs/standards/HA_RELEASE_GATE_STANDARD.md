# HA Release Gate Standard

**Status:** Draft v1.0 (2026-05-25)
**Owner:** Platform / orchestrator (Power Lane for automation enforcement)
**Audience:** RyzaLab operator + every agent that authors or merges production HA automation changes in customer repos
**Scope:** Every production Home Assistant automation change in every customer repo (`ryzalab-austin-main`, `ryzalab-par-main`, `ryza-willr-main`, future `ryzalab-<sitecode>-main`)
**Companion:** [`docs/prd/PRD_AI_OPS_AND_HA_DELIVERY_FACTORY_v0.2.md`](../prd/PRD_AI_OPS_AND_HA_DELIVERY_FACTORY_v0.2.md) §10 (originating proposal)

## Why this exists

RyzaLab delivery is repeatable only when every production HA change carries the same evidence. Without a codified gate, gate completeness depends on operator memory on the day — which scales poorly past N=3 paying homes and breaks the [PMRD v0.2](../prd/PMRD_EZRA_MENTOR_REVIEW_v0.2.md) §6 reliability and recovery commitments to customers.

This standard turns the per-change gate from operator memory into machine-readable attestation, so the [HA Delivery Factory](../prd/PRD_AI_OPS_AND_HA_DELIVERY_FACTORY_v0.2.md#5-ha-delivery-factory-new) lifecycle has a single inspectable choke point at the deploy step.

## The substantive policy

### 1. Gate scope

The HA Release Gate applies to **every production HA automation change in customer repos** that:

- Modifies `configuration.yaml`, `packages/*.yaml`, `automations.yaml`, `automations/*.yaml`, `scripts.yaml`, `scenes.yaml`, `groups.yaml`, or files under `dashboards/`.
- Adds, removes, or reconfigures a `custom_components/*` install.
- Bumps the pinned platform version (`PLATFORM_VERSION`) and refreshes `docs/UPSTREAM/` in a way that touches a runtime contract.
- Modifies any entity reference under the customer's `[SITE]-*` namespace per [`VALIDATION.md`](VALIDATION.md).

It does **not** apply to:

- Customer-repo docs-only changes (e.g. `docs/DECISIONS.md` annotation without YAML)
- Platform-repo changes (governed by `CONTRIBUTING.md` Risk Tiers and the QA closeout contract)
- Operator-side tooling that does not touch the appliance

### 2. The seven required attestations

**No production HA automation change is complete until all seven are green:**

| # | Attestation | Acceptable evidence |
|---|-------------|---------------------|
| G1 | **Current config validates** | `ha core check` (or site equivalent) exits 0 against the change; CI artifact or operator-attested log line in PR Evidence |
| G2 | **Pre-change *full* backup exists, integrity-checked** | Fresh **full** backup tarball present + size > 0 + manifest parses **and confirms the archive contains the HA configuration and the database/`.storage`** (not a partial/addon-only slice — restore is the only prescribed rollback, so a partial backup is not a valid one; see §4a). Backup ID + timestamp recorded in PR Evidence. *Per-change restoration test is **not** required here — that is the separate periodic drill (§3 below).* |
| G3 | **Rollback path documented** | Concrete steps + target RTO recorded in PR Evidence (per package's `ROLLBACK_CHECKLIST.md` from delivery factory templates) |
| G4 | **Affected entities available** | Entity-registry check + ping against the `[SITE]-*` entities touched by the change. PR Evidence includes the entity-set queried + result |
| G5 | **Automation smoke test passes** | Per the change's `POST_DEPLOY_SMOKE_TEST_CHECKLIST.md`. PR Evidence includes each row pass/fail + timestamp |
| G6 | **Telemetry / report snapshot generated** | Per `TELEMETRY_REPORT_TEMPLATE.md`. Snapshot file present + timestamp in PR Evidence |
| G7 | **Customer-facing handoff notes updated** | Per `CUSTOMER_HANDOFF_REPORT_TEMPLATE.md`. PR Evidence references the updated handoff doc |

Templates for G3 / G5 / G6 / G7 live in `docs/templates/packages/` (delivered by HA Delivery Factory MVP — PRD §7).

### 3. Backup integrity vs restoration drill — two cadences

Per PRD §10 clarification:

| Cadence | What is verified | Where it runs |
|---------|------------------|---------------|
| **Per-change** (G2 in this gate) | Backup operation succeeded; tarball present + integrity-checked (size > 0, manifest parses); SHA recorded | Inline before any production deploy |
| **Periodic** (separate, not gating per change) | Actual restoration to a scratch HA instance succeeds; recorder + entities post-restore match expectations | Monthly drill per [`docs/runbooks/health-check-protocol.md`](../runbooks/health-check-protocol.md) § Backup restore drill; tracks against PMRD v0.2 §6 KPI |

Per-change restoration would block every deploy and discourage small frequent changes — opposite of the package-delivery cadence. Periodic drills provide the same assurance at sustainable operator cost.

### 4. Enforcement model

**v1 (today, this release):** **Operator-attested.** Every customer-repo PR carrying an in-scope change posts an `HA-RELEASE-GATE:` block in its PR description (or as a single review comment) with G1-G7 attestations.

```text
HA-RELEASE-GATE: PASS
G1 config validates: <evidence>
G2 backup integrity-checked: <backup id + timestamp>
G3 rollback documented: <link to ROLLBACK_CHECKLIST.md row>
G4 entities available: <entity-set queried + result>
G5 smoke test passed: <link to POST_DEPLOY_SMOKE_TEST_CHECKLIST.md row>
G6 telemetry snapshot: <link to TELEMETRY_REPORT_TEMPLATE.md instance>
G7 handoff updated: <link to CUSTOMER_HANDOFF_REPORT_TEMPLATE.md instance>
```

PR cannot be merged-to-prod until the block is green.

**v2 (Phase 2+ of AI Ops, per PRD):** Automation layer writes a gate-attestation row to Notion (new database or extension of QA Log) before allowing the deploy commit. The block above continues to live in the PR as human-readable evidence; the Notion row becomes the audit-grade record.

**v3 (post-Phase 3 or per-customer GA):** GitHub Actions CI job blocks merge unless the gate block is present and all 7 rows say `PASS`.

This standard intentionally specifies the **policy** at all three enforcement levels; the implementation cutover is a separate decision.

### 4a. Deterministic pre-merge validation — the CI layer (v1.1)

*Validated 2026-07-24 by three independent research reviewers (HA official docs · HA community/practitioners · CI/CD determinism), cross-checked against `frenck/home-assistant-config` CI, the `home-assistant.io` `check_config` docs, the HA GitOps community thread (2026-07-16), and GitHub required-status-check docs. Convergent verdict: the on-host deploy chain (G1–G7 + `deploy_ha.sh`) is at or above best practice, but pre-merge CI must do three things it currently does not.*

**Why CI is the authority — not local hooks, not on-host checks.** The deterministic, server-enforced layer is the *server-side required check*. Local git hooks are `core.hooksPath`-based — per-clone, uncommitted, `--no-verify`-skippable, and silently absent on a fresh clone or a non-Claude agent — so they are **fast-feedback only, never the authority**. On-host `ha core check` owns *deploy-time, exact-version* safety but runs only *after* the ref is on the box (detection, not prevention). At **fleet scale** (customer instances on heterogeneous HA Core versions) a config valid on one version can break another; only a central, pinned, per-version CI gate catches that *before* merge.

*Server-enforced is not un-bypassable, and required-check pinning is policy, not cryptography.* A repo admin can still relax protection; a write-actor who can edit the workflow file can make it emit green; and a required status pinned to an App is trusted-by-policy, not cryptographically bound to the tree. So the required check must be paired with **CODEOWNERS review on `.github/workflows/`** and a change-controlled ruleset. This gate raises the cost of shipping a bad config to "defeat branch protection," not to zero.

Three required CI properties, in addition to the G1–G7 attestations:

1. **CI runs a real HA config check** — not merely an operator-attested `ha core check` log line. Each customer repo runs `frenck/action-home-assistant` (or `hass --script check_config`) **matrix-tested against the HA Core versions the fleet runs — at minimum `stable` and `beta`** — with a committed **stub secrets file** ([`docs/templates/stub_secrets.example.yaml`](../templates/stub_secrets.example.yaml) → repo-root `stub_secrets.yaml`). This catches HA-invalid-but-YAML-valid configs and forward-deprecations (e.g. the 2026.6 legacy-template removal) that lint and the governance `unittest` suite cannot. Reference workflow: [`docs/templates/ha-config-check.reference.yml`](../templates/ha-config-check.reference.yml). **Pin the action to a full commit SHA** in the adopted workflow — a mutable `@v1` tag is not a deterministic gate. This upgrades **G1** from "CI artifact *or* operator-attested" to "**CI-enforced HA config check required**."

2. **Deploy is gated on a CI-green SHA.** The on-host `git_pull_config` / `deploy_ha.sh` must only fast-forward to a `main` SHA for which **every required matrix leg's Check Run reports `conclusion == success`** — assert the exact-SHA Check Runs via the GitHub Checks API before pulling (a `skipped`/`neutral` leg is not a pass, and legacy commit-status is weaker than the per-job Check Run). Without this, a force-push or admin-merge can place an unvalidated ref on `main` for the box to pull; CI would then be protecting the merge button, not the box.

3. **The CI check is REQUIRED and trustworthy.** Set it as a **required status check on `main`, pinned to a specific trusted GitHub App, with `enforce_admins` on**, and add **CODEOWNERS review on `.github/workflows/`** so the gate can't be edited to self-green. Pinning is policy, not cryptographic binding (see the note above) — any write-actor can otherwise post a green status, and an admin could relax protection. This is the §4 v3 enforcement level made concrete for the HA config check.

**Rollback correction (updates G2 + G3).** The documented rollback is **Supervisor backup restore** (`ha backups restore <slug>`), **never `git reset --hard origin/main`**. A hard reset touches only *git-tracked* files — it does **not** restore untracked runtime state (`.storage/`, the database) that a bad release may already have written or migrated, and it cannot undo a schema migration. Only a Supervisor backup restore recovers the full instance state; a hard reset gives a false sense of rollback while leaving a migrated store in place.

*Restore is a valid rollback only if the backup is a FULL backup.* Prescribing restore as the sole rollback puts a **contents** requirement on G2 that a mere existence check does not satisfy: G2 must verify the archive is a **fresh full backup containing the HA configuration and the database/`.storage`**, not merely that a non-empty tarball with a parseable manifest exists. A partial backup (config-only, or an addon slice) passes a size/manifest check yet cannot recover a migrated store — so a release could clear all seven attestations with no usable rollback after a migration. G2 therefore requires and verifies full-backup contents before restore counts as the rollback (see the updated G2 row above).

**Layering — which check lives where:**

| Layer | Runs on | Authority for | Bypassable? |
|---|---|---|---|
| Local git hooks | commit / push | fast lint feedback | **Yes** (per-clone, `--no-verify`) — advisory only |
| **CI (required, pinned App, `enforce_admins`)** | every PR | lint + governance `unittest` + **HA config check (stable/beta)** | Only by admin/ruleset change or a CODEOWNERS-unguarded workflow edit — the deterministic gate |
| On-host at deploy | `deploy_ha.sh` / ha-mcp | verified backup → `ha core check` (exact version) → restart → smoke test | operator-gated; last-mile safety net |

**Rollout:** scaffolded here in `ryzalab-platform`; each customer repo (`ryzalab-austin-main`, `ryzalab-par-main`, `ryza-willr-main`, future `ryzalab-<sitecode>-main`) adopts the reference workflow, copies `stub_secrets.example.yaml`, sets the check required (SHA-pinned action, `enforce_admins`, CODEOWNERS on workflows), and adds the deploy-host CI-green-SHA assertion (req 2). A concrete branch-protection/ruleset artifact naming the exact required matrix contexts and App ID is an adoption deliverable per repo — the highest-drift surface — tracked in the rollout backlog, not baked in here.

**What the deterministic test covers — honestly.** `tests/test_ha_release_gate_standard.py` locks the *platform-controlled* surface: the reference workflow's structure (real config-check action, `stable`+`beta` matrix, stub-secrets wiring, read-only permissions, `main` triggers), that §4a names all three requirements and the corrected rollback, and that `make validate` runs the test. It **cannot** verify a customer repo's live branch protection or that its `deploy_ha.sh` asserts the CI-green SHA — those are req 2/3 and are verified at customer-repo adoption, not by this platform test. The test prevents the *standard and its reference artifact* from drifting apart; it does not by itself prove any box is protected.

### 5. Failure-mode handling

| Scenario | Disposition |
|----------|-------------|
| Any of G1-G7 fails | PR cannot merge until the underlying issue is fixed; the gate block is updated to reflect the failure and the remediation commit |
| Customer requests emergency change (e.g. broken automation blocking household) | Operator may post `HA-RELEASE-GATE: EMERGENCY-OVERRIDE` with a one-line justification, the gate block as-far-as-completed, and a follow-up Notion Backlog row to close gaps within 48 hours. Emergency overrides count against the change-failure-rate KPI (PMRD §6) |
| Gate template (`POST_DEPLOY_SMOKE_TEST_CHECKLIST.md` etc.) does not exist for the package type | Operator may attest manually for the missing template **once**, then files a Backlog row to add the template (per HA Delivery Factory MVP exit criteria, PRD §7.2) |
| Change touches no in-scope files (docs-only, comment-only) | Gate does not apply; standard PR review continues |

## Tripwires

Revisit this standard when any of these fire:

- **Override rate > 10%** of in-scope PRs over a 4-week rolling window — gate is too strict or templates are missing; tighten or relax accordingly
- **Change failure rate exceeds PMRD §6 threshold** (>10% per package) despite gate-PASS verdicts — gate is missing a real failure mode; add a G8 or expand an existing row
- **Restoration drill (§3 periodic) fails** more than once per quarter — per-change G2 may need to incorporate a quick sanity-restore step
- **Customer pin-bumps lag platform releases by > 30 days** — the gate may be over-coupled to platform changes; loosen
- **N reaches 5 paying homes** — re-evaluate v1 operator-attested model; promote to v2 automated attestation in Phase 2

## Out-of-scope

- **Platform-repo changes.** Governed by `CONTRIBUTING.md` Risk Tiers (Draft / Confirm / Blocked) and the QA closeout contract. The HA Release Gate applies only to customer-repo HA changes.
- **Bench / staging-only deploys** that never touch a customer's production HA instance. Use this gate as an aspirational rehearsal, not a hard block, for bench work.
- **Customer-initiated rollbacks** (where the customer-side operator reverts via the rollback path G3 documented). The gate ratifies a forward change; rollback is a different operation governed by `health-check-protocol.md`.
- **Multi-tenant scenarios** (a single deploy touching multiple customer sites). RyzaLab is per-customer-per-repo; multi-tenant work is out of scope.

## Revision history

| Date | Author | Version | Summary |
|------|--------|---------|---------|
| 2026-05-25 | platform | v1.0 (Draft) | Initial standard. Codifies PRD §10 HA Release Gate as a customer-repo-enforceable contract. 7 attestations (G1-G7), two-cadence backup model (per-change integrity + periodic drill), three-level enforcement plan (v1 operator-attested → v2 Notion-automated → v3 CI-blocked), failure-mode and emergency-override handling, tripwires for revisit. |
| 2026-07-24 | platform | v1.1 (Draft) | Added §4a "Deterministic pre-merge validation — the CI layer" from a 3-independent-reviewer research validation (HA official / HA community / CI-CD determinism). Requires a real HA config check in CI (`frenck/action-home-assistant`, matrix stable+beta, stub secrets) — upgrades G1; requires deploy gated on a CI-green SHA; requires the check be a pinned, `enforce_admins` required status check. Corrects G3 rollback to Supervisor backup restore (never `git reset --hard`), and tightens G2 to require a verified *full* backup (archive contains HA config + database/`.storage`, not just a non-empty tarball) so restore is a valid rollback. Reference workflow `docs/templates/ha-config-check.reference.yml` + `docs/templates/stub_secrets.example.yaml`; deterministic test `tests/test_ha_release_gate_standard.py`. |
