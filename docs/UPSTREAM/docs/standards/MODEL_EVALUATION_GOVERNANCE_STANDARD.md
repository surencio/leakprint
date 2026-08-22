# Model-Evaluation Governance Standard

**Status:** Proposed (cross-family reviewed 2026-07-21, PASS-WITH-CHANGES applied)
**Owner:** RyzaLab founder
**Audience:** The operator + any agent selecting or reassigning a model for an agent role or a one-off task (Claude Code, Codex, Cursor).
**Scope:** How RyzaLab evaluates and picks models across the eight variables using external benchmarks — covers router role assignments and one-off model choices, cross-customer (platform SSOT, consumed by customer repos via pinning). Out: model safety/alignment policy, and any bespoke/maintained benchmark.
**Risk tier:** Confirm

## Why this exists

RyzaLab assigns models to agent roles (orchestrator, challenge/red-team, validate, heartbeat) and picks models for one-off tasks. That choice must be **evidence-based, not habit** — a frozen role→model matrix is the DHM-16 failure mode (a constraint nobody re-checks as the frontier moves). But at this stage RyzaLab is a solo-founder pilot and **must not own a maintained benchmark index or golden set** — the maintenance cost is not justified yet. This standard resolves the tension: **consult an external, third-party-maintained framework as a governance input, and cover the few things it cannot measure with cheap, per-decision spot-checks — never a maintained set.**

Decided and reviewed by cross-family review (2026-07-21): codex `gpt-5.5/high` (best-fit challenger, live-web with citations) + qwen + composer-2.5 heartbeat. The framework decision converged; this document's fixes (evidence packet, per-decision prompts, tiered runbook, fact corrections) come from that review.

## The eight evaluation variables

reasoning · knowledge · coding · math · agentic · price · speed · latency.

## Decision — external anchor + one complement, zero maintained index

| Role | Framework | What it supplies | Version-pin |
|------|-----------|------------------|-------------|
| **Primary anchor** | **Artificial Analysis** (artificialanalysis.ai) | Evidence for all 8 variables across its **benchmark, capability, pricing, and performance surfaces**: the **Intelligence Index** (composite) plus the separate **Agentic Index** and **Coding Index**; and separate **price** / cost-per-task, **output speed** (tok/s), **latency** (TTFT, end-to-end; P50 over ~72h) surfaces | Pin `intelligence_index_version` (currently **v4.1**, June-2026-current: Agents 34% / Coding 24% / Scientific Reasoning 24% / General 18%; v4.0 removed MMLU-Pro, LiveCodeBench, AIME) |
| **Contamination complement** | **LiveBench** (livebench.ai) | Contamination-resistant cross-check: 23 tasks across 7 categories (reasoning, coding, math, data-analysis, language, IF, agentic-coding) + cost-per-successful-task | Pin the dated release shown on **livebench.ai** (currently **Release 2026-06-25**; ~6-month full refresh, delayed question release, objective grading). Cite the site, **not** the GitHub changelog (which lags — tops out at 2026-01-08). |
| **Chat-taste tie-breaker (optional)** | LMArena | Human-preference Elo — **only** for chat/user-facing roles, as a tie-breaker; never a capability or agent-governance score | Note the snapshot date |

**Rule of thumb:** AA sets the shortlist → LiveBench **cross-checks for contamination-sensitive disagreement** → LMArena breaks ties on UX (chat roles only).

**Honest coverage limit:** AA can supply *evidence* for all 8 variables, but the Intelligence Index itself is **not** a combined role-governance score, and its price/speed/latency figures are **endpoint- and workload-specific**, not measured under RyzaLab's harness. Read the sub-surfaces (Agentic/Coding indices, the price/speed/latency tables), not just the headline composite.

**Rejected as anchors/complements** (recorded so the choice is auditable): SEAL/Scale (strong private-holdout story, uneven public usability, no speed/latency surface); SWE-bench / Aider / Terminal-Bench (good agent-coding spot signals but too narrow to govern 8 variables; SWE-bench has contamination/design caveats; Aider's leaderboard is 2025-vintage — verify freshness at use). These may be used as *spot-checks*, not as the governing reference.

## What NO external framework covers — per-decision spot-check, never a maintained set

Three axes are invisible to every leaderboard and must be checked **once, at selection time, for the leading candidate** (the single finalist the Tier 2 runbook narrows to — not every candidate) — a pre-adoption smoke test, "a hiring interview, not a golden set":

1. **Reliability / determinism / prompt-fidelity.** Replay a few runs of the candidate on **prompts sampled per-decision from recent real RyzaLab work** (see the maintenance guard below); log pass@k, output variance, instruction misses, refusal drift. This is the axis that, in our own experience, let a low-index model out-catch larger ones. **Secret-safety gate (mandatory):** a candidate is frequently an *unapproved or external* model/provider, so the sampled prompt **must be secret-safe before replay** — redacted or synthetic, or passed through a secret-safety check (per `docs/experiments/REVIEW_PRECONDITIONS.md` precondition #14, "Inputs are secret-safe"). Never replay un-redacted customer config, incident details, or credentials against a model outside the approved route; that turns the spot-check into an exfiltration path.
2. **Cross-provider decorrelation.** For the challenge/red-team role, ensure at least one reviewer is a **different lab/model family** from the artifact's author. No index measures this; it is an explicit dependency check, not a score. Cross-family decorrelates *models*, not *premises* (see REVIEW_PRECONDITIONS #11).
3. **Toolchain fit.** One cheap run of the exact agent role under our harness (MCP tools, retries, schema adherence, stdin/file ingestion): "follow these constraints, produce this artifact, do not invent state."

**Maintenance guard (load-bearing).** The spot-check prompts are **sampled per decision from recent real work or an existing smoke path** and logged *as evidence of that decision*. They are **never promoted into a standing benchmark suite**, curated, or refreshed on a schedule — that would recreate the maintained golden set this standard exists to avoid. If you find yourself maintaining the prompt set, stop: that is the tripwire that this standard has been violated.

## Selection-Time Runbook (normative — run in ≤35 min, two tiers)

**Tier 1 — Gate (~15 min, always).** Look up the finalists on AA across the 8 variables; check each is present on LiveBench and note any contamination-sensitive disagreement. Reject obvious bad picks here. Do **not** run spot-checks yet.

**Tier 2 — Adopt (~≤20 min add-on, one finalist only).** For the single leading candidate: collapsed spot-check #1 (**~3 runs × 1 sampled prompt**, not a battery), the decorrelation check (#2), and one harness run (#3). Do **not** run the full spot-check on multiple finalists in one session — narrow on AA/LiveBench first, then interview the winner. (Gate ~15 + Adopt ~20 = ≤35 min.)

Fill the Evidence Packet below as you go; the packet **is** the record.

## Model Selection Evidence Packet (mandatory for every role reassignment)

A role reassignment or a governed model choice is **not complete without this packet.** Store it in the router-ADR change PR's evidence section, or as a dated file under `docs/artifacts/model-selection/`. An agent that writes "checked AA/LiveBench" without a packet has left no auditable artifact and the change is not governed.

```text
model:                          # e.g. claude-opus-4-8
role:                           # router role (per ADR-model-router-control-plane): orchestrator | implementer | reviewer | researcher | heartbeat | safety  — challenge/validate are review overlays on reviewer/safety; or one-off:<task>
candidates_considered:
aa_intelligence_index_version:  # e.g. v4.1
aa_snapshot_date:
aa_scores:                      # intelligence / agentic index / coding index
aa_price_speed_latency:         # $/Mtok, tok/s, TTFT (note endpoint)
livebench_release:              # e.g. 2026-06-25 (from livebench.ai)
livebench_present:              # yes | no | n/a  (+ category notes / disagreement)
lmarena_snapshot_date:          # chat-facing roles only, else n/a
variant / reasoning_effort / endpoint:
spotcheck1_reliability:         # pass@k + variance on the sampled prompt(s); prompt source
spotcheck1_prompt_secret_safe:  # REQUIRED before replay vs external/unapproved model: redacted | synthetic | secret-checked
spotcheck2_decorrelation:       # yes | n/a (name the distinct family)
spotcheck3_harness:             # pass | fail | skipped
decision:                       # adopt | reject | defer
reviewer / approver:
tripwire_notes:
```

## The single binding caveat

**External benchmarks are governance *inputs*, not governance *decisions*.** Pin the source, date, index version, model variant, reasoning-effort setting, and endpoint (the packet enforces this). Never treat a composite rank as proof a model is reliable for the actual RyzaLab role — leaderboards optimize composite scores under fixed harnesses; production optimizes reliability, latency SLOs, and tool-call success on *our* prompts, and rankings routinely invert in the wild.

## When to consult (cadence — no maintained schedule)

- **At model-selection time** for any role or task (the runbook + evidence packet).
- **On a tripwire**, not a calendar. Any AA or LiveBench release that changes **benchmark composition, task subsets, graders, scoring/normalization, category weights, anchors, or refresh generation** triggers a **Tier 1 re-evaluation** — do **not** decide re-evaluation from the major/minor version number alone (AA "minor" bumps have changed weights and benchmarks; v4.1 itself replaced benchmarks and adjusted weights). A purely **data-only** update, model addition, price/availability change, or documentation correction may **update the pin** without re-running selection, *unless* it changes the finalist set or economics materially. A **new frontier model** in a role's candidate set is also a trigger. Read the source's release notes at selection time and record the reason in `tripwire_notes` — there is no automated watcher, and that is an accepted limit at this stage.
- Explicitly **no maintained golden set and no fail-closed demotion harness at this stage** — reviewed and deferred (the maintenance cost is not yet justified; revisit if RyzaLab moves past the solo-founder pilot).

## Out of scope

- A bespoke RyzaLab benchmark, golden set, or continuously-run eval harness (deferred by decision above).
- Auto-routing role assignment directly from any composite index (rejected by cross-family review 2026-07-20 — the composite is cost-blind, has no independence or reliability axis, and is the wrong denominator per role).
- Model safety/alignment red-teaming policy (separate standard).

## Relationship to other governance

- Feeds `docs/adr/ADR-model-router-control-plane.md` and the agent-role-matrix: this standard is the **evidence source**; the router ADR is the **change-management wrapper** (who may reassign a role, and how it is logged). The Evidence Packet is the artifact the ADR's change PR carries.
- A role reassignment is a Confirm/Blocked-tier control-plane change (logged, distinct-reviewer or operator per tier).

## Tripwires (this standard is wrong / stale if…)

- A cited model choice has **no Evidence Packet** (or no pinned source/date/version) → unauditable, treat as no evidence.
- AA or LiveBench changes methodology and the pin is not updated → the number no longer means what the doc says.
- The spot-check prompt set is being **maintained, curated, or refreshed on a schedule** → a stealth golden set; stop (see the Maintenance guard).
- A role reassignment happens without the 3 spot-checks → the invisible axes were skipped.
- A spot-check replays **un-redacted real work against an external/unapproved model** → potential customer-data/secret leak; stop and redact (see spot-check #1 secret-safety gate).

## Revision history

- v0.1 (2026-07-21) — initial draft; framework decision (AA anchor + LiveBench complement, no maintained index) from cross-family review (codex + composer converged on it, facts verified by codex against live sources). Document then hardened per the cross-family review of the draft (codex + qwen + composer, all PASS-WITH-CHANGES): added the mandatory Evidence Packet, the per-decision Maintenance guard on spot-check prompts, the tiered Selection-Time Runbook, and fact corrections (Agentic Index / Coding Index exact names; cite livebench.ai not GitHub; softened AA coverage and the LiveBench cross-check wording).
- v0.2 (2026-07-21) — merge-readiness cross-family round on PR #110 (codex + qwen + composer). Fixed three blocking findings: the version-bump cadence now triggers re-evaluation on any methodology-affecting release rather than by version number (AA "minor" bumps change weights — codex, verified against AA's data-api versioning); the Evidence Packet `role` field now matches the six router-ADR roles instead of an incomplete set (composer); and the runbook time budget is internally consistent (Gate ~15 + Adopt ~20 = ≤35 min, not ≤30 — composer). Also fixed a codex-connector P2 (secret-safety): the reliability spot-check now requires redacted/synthetic/secret-checked prompts before replaying real work against an external/unapproved model, the secret-safe-inputs precondition — else the mandatory spot-check would be a data-exfiltration path.
- v0.3 (2026-07-21) — codex-connector automated review (round 2) raised three more P2s, all fixed: added the required **Audience** and **Scope** header fields (CONTRIBUTING.md new-standard contract); resolved a candidate-scope contradiction (the three invisible-axis checks run for the **leading candidate**, matching the Tier 2 runbook, not "per candidate"); and corrected the secret-safety citation to `docs/experiments/REVIEW_PRECONDITIONS.md` **precondition #14** (the invented anchor name is gone).
