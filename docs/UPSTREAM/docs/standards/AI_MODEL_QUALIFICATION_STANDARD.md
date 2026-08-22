# AI Model Qualification Standard

**Status:** Proposed
**Owner:** RyzaLab founder (AI PM role)
**Audience:** The orchestrator, any agent that selects a model for a task, and any repository maintainer who consumes a routing decision.
**Scope:** How RyzaLab qualifies a model for a **task class**, how a route is pinned and replaced, what evidence a qualification must leave behind, and when a route must be requalified. Cross-customer; platform is the single source of truth and customer repos consume it by pointer. Out of scope: model safety and alignment policy, the control-plane change-management wrapper (that is [`ADR-model-router-control-plane.md`](../adr/ADR-model-router-control-plane.md)), and any live customer deployment.
**Risk tier:** Confirm
**Authority:** Git. Notion is a discovery index and can never overwrite a canonical file.

**Occupant boundary status:** `OCCUPANT_BOUNDARY_UNPROVEN`

This marker is normative and stays until MQ-F1, the lab tenant-token negative
test battery, passes in an authorized lab. While it reads `UNPROVEN`, no
document, proposal, PR body, or customer commitment may describe the occupant
authorization boundary as proven, verified, or production-ready. Removing the
marker is not a way to satisfy the rule; passing MQ-F1 is.

> **Merge dependency, blocking for Task B.** Task B is scored against
> `docs/standards/HA_OCCUPANT_CONTROL_STANDARD.md`, which is **not on `main`**. It is
> unmerged on `feat/commissioning-contract-closure` at commit `25ce339`. Until that
> branch lands, a reader on `main` cannot open the authority Task B depends on, so
> **Task B qualification is not usable from `main`** and its pinned winner must not be
> relied on there. Task A, Task C, the harness, and the registry are unaffected.
> Closing condition: merge `feat/commissioning-contract-closure`, then re-run
> `make validate` so the link check proves the reference resolves.

## 1. Why this exists

RyzaLab pays for inference on every task an agent performs, and the cost gap
across the catalog is roughly three orders of magnitude. Choosing one permanent
frontier model for everything overpays for extraction and formatting. Choosing
the cheapest model for everything produces confident, wrong security findings.

This standard resolves both by refusing to answer "which model is best." It
answers a narrower question that has a measurable answer: **for this task class,
which is the least expensive pinned model that clears a fixed quality floor?**
The floor comes first, cost decides among survivors, and no selection is
permanent.

[`MODEL_EVALUATION_GOVERNANCE_STANDARD.md`](MODEL_EVALUATION_GOVERNANCE_STANDARD.md)
governs the adjacent question of which *external framework* informs a role
assignment, using published leaderboards. This standard governs qualification
against **RyzaLab's own bounded fixtures**, which no leaderboard measures. Where
the two disagree about a specific route, the executed fixture result wins,
because it was measured under our harness on our task.

## 2. Authority and evidence hierarchy

Highest wins.

1. **Executed tests and pinned source.** A trial recorded in a run artifact, or
   a line in a version-pinned source fixture.
2. **Live negative tests against a lab instance.** Reachability at runtime is
   not provable by reading source.
3. **The published standards and schemas in this repository.**
4. **Provider and catalog metadata**, as a dated observation, never a promise.
5. **Model prose.**

Model voting never resolves a disputed finding. Two models agreeing is one
correlated observation, not evidence. Disagreement is settled by adding a test
or a pinned citation, or by recording the question as unresolved.

## 3. Task-risk and complexity classification

Every task class carries a tier. The tier sets the quality floor and who may
approve a route change.

| Tier | Meaning | Examples | Quality floor | Route change approved by |
|---|---|---|---|---|
| **T3 security-critical** | A wrong answer can grant an occupant, tenant, or agent authority they should not have | Authorization-boundary review, capability classification, tenant acceptance matrix | Every critical gate passes, accuracy at or above 0.90, consistent across 3 trials | Human operator |
| **T2 governed** | A wrong answer produces a bad artifact that a reviewer would probably catch | Standards edits, runbook generation, effect-graph construction | Every critical gate passes, accuracy at or above 0.80 | Distinct reviewer |
| **T1 routine** | A wrong answer is cheap to detect and cheap to redo | Extraction, inventory, formatting, schema generation, routine YAML, status text | Schema-valid, accuracy at or above 0.70 | Self, with the run artifact |

A task class with no tier is **T3 by default**. Fail closed.

## 4. Catalog consideration

At the start of every qualification run:

1. Fetch and store a **timestamped, hashed snapshot** of the OpenRouter catalog
   and provider list.
2. Record a result for **every model in the snapshot**. A model is either a
   candidate or carries at least one machine-readable exclusion code. Silence is
   not an outcome.
3. "Consider" means evaluate through catalog metadata and prior qualification
   records. It does not mean invoke.

### 4.1 Hard filters

A model that trips any of these is excluded before any inference.

| Code | Excluded because |
|---|---|
| `E01_NO_TEXT_OUTPUT` | No text output modality |
| `E02_NO_STRUCTURED_OUTPUT` | No `response_format` or `structured_outputs`; cannot satisfy an output contract |
| `E03_NO_TOOL_SUPPORT` | The task class requires tool calling and the model advertises none |
| `E04_INSUFFICIENT_CONTEXT` | Context or completion cap below the task's floor |
| `E05_UNPINNABLE_ROUTE` | Auto, fused, or meta route: the executing model is chosen at request time |
| `E06_NONDETERMINISTIC_VARIANT` | Variant suffix routes or augments the request non-deterministically |
| `E07_FREE_VARIANT_DATA_POLICY` | Free variant: acceptable retention and no-training cannot be asserted |
| `E08_BATCH_ONLY_VARIANT` | Asynchronous batch variant, outside the interactive harness |
| `E09_ALIAS_NOT_STABLE` | Alias target: the slug can be repointed without a version change |
| `E10_NO_SAMPLING_CONTROL` | No temperature control, so low sampling cannot be met |
| `E11_LIFECYCLE_EXPIRING` | Carries an expiration date; not durable enough to pin a route to |
| `E12_UNPRICED` | No usable price, so expected completion cost cannot be computed |
| `E13_PROVIDER_POLICY_UNKNOWN` | Provider publishes no privacy policy or terms |
| `E14_PROVIDER_UNHEALTHY` | Endpoint status or uptime below the health floor |
| `E15_NO_ENDPOINT` | No servable endpoint published |

### 4.2 Privacy and provider gates

Enforced **before** price is compared, never after.

- Strip secrets, tokens, private keys, customer identifiers, and live
  credentials from every prompt before external inference. The harness runs a
  deny-list scanner and **withholds the request** on a match rather than
  redacting silently. A fixture that trips the scanner is fixed; the scanner is
  not loosened.
- Every executed request sets provider routing to deny prompt collection, with
  fallback disabled. A provider that will not serve under that constraint is
  excluded, not accommodated.
- Record the provider name, headquarters, datacenters, privacy-policy URL, and
  terms URL for every executed trial. A provider that publishes neither URL
  cannot pass the gate.

### 4.3 Pinning

Qualification and security acceptance run against an **exact model slug and a
single named provider**, with fallback routing disabled. An automatic, latest,
random-free, or fused route is never qualified and never accepted for a
security-critical task class, because the artifact would not describe what
actually ran.

Sampling is low and recorded: temperature 0, top_p 1, a fixed seed where the
model supports one, and a declared output contract. **Reasoning effort never
exceeds `high`.** The harness clamps anything higher rather than failing, and
records the clamp.

## 5. Staged qualification

Token spend is conserved by testing in widening circles, not by testing less
carefully.

**Stage 1 — metadata and cached-result screening.** Whole catalog, no
inference. Apply §4.1 and §4.2. Reuse a prior qualification record **only** when
all of these still match exactly: model slug, provider, model version, harness
version, fixture hash, prompt hash, tool configuration, sampling configuration.
Any mismatch invalidates reuse; there is no partial credit.

**Stage 2 — bounded screening.** Run the smallest representative fixture
against the cheapest qualified candidate in each distinct model family. Remove
anything that fails a critical accuracy, schema, instruction, or safety
requirement. Screening on one family member is a deliberate economy and a
recorded limitation: it can miss a more capable sibling in an eliminated family.

**Stage 3 — full bake-off.** Run all bounded task classes for the candidates
still on the cost/quality frontier.

**Stage 4 — reliability confirmation.** Repeat **finalists only**, enough times
to measure consistency. A disqualified model is not repeated; repeating it buys
no information and costs money.

**Escalation.** If a task class ends with no qualified winner, the next round
may add more capable candidates. The escalation and its reason are recorded in
the run. Gates are never relaxed to produce a winner.

## 6. Scoring and winner selection

### 6.1 Measured

Factual accuracy against hidden ground truth; missed escalation paths; invented
claims; instruction compliance; machine-readable output validity; consistency
across trials; input, output, reasoning, and cached tokens; actual provider
cost; elapsed time; retry count; and human correction or rework.

Ground truth is never sent to a candidate. Scoring is mechanical: no model
grades another model's answer.

### 6.2 Gate construct

A gate must measure the hazard, not the appearance of caution. Where a task has
an asymmetric failure mode, the two directions score differently and the
standard says so explicitly. In capability classification, **granting more than
the standard allows is a security failure and fails a gate; granting less
destroys a capability and costs accuracy, but does not fail the security gate.**
A gate that treated them identically would reward a model that answers
"protected" to everything.

### 6.3 Decision order

1. Apply every critical pass/fail gate.
2. Compute quality and reliability **only among models that passed**.
3. Select the **lowest expected completion cost** among those at or above the
   tier's quality floor.
4. Report the Pareto frontier when cost and quality do not produce one dominant
   result.
5. Use elapsed time only as a secondary tie-break.

Never select a cheaper model that misses a critical finding. Never select a more
expensive model when a cheaper one clears the same floor reliably.

### 6.4 Expected completion cost

Advertised token rates are not the cost. Expected completion cost is:

```text
mean_token_cost_per_attempt / observed_pass_rate
  + (1 - observed_pass_rate) x rework_minutes/60 x founder_hourly_rate
```

Retries, malformed output, and validation failures are already inside the
numerator because a failed attempt still bills its tokens. Rework is expressed
in founder minutes, the unit the governance cost ledger already uses, and
converted once, in the harness, with the rate recorded in the run artifact.

The default of 10 founder minutes per failed trial is an **assumption, not a
measurement**. It is recorded as such and should be replaced by observed
per-episode rework once the cost ledger carries enough rows.

### 6.5 Independent winners

A winner is chosen **per task class**. There is no overall winner, and the
standard does not name one.

## 7. Model routing

Frontier models are permitted for: orchestration; significant research;
cross-repository reconciliation; security-critical ambiguity; difficult
implementation or debugging **after** a lower-cost qualified model has failed;
and final acceptance where the consequence justifies the cost.

Efficient models are the default for: extraction; inventory; formatting; schema
generation; clear documentation edits; routine YAML; bounded test generation;
heartbeats and status.

Escalation is evidence-driven. "This feels hard" is not a reason to route to a
frontier model; a recorded failure by the qualified route is.

### 7.1 Codex lane

Observed behavior, recorded so it is not rediscovered:

- Route Codex to **file-producing** lanes, not response-only analysis.
- Deliver the prompt through **stdin**.
- Give each Codex writer **workspace-write in its own worktree**.
- Judge completion by the **requested files, a scoped diff, validation, and a
  commit** — not by the transcript.
- Capture stderr for diagnostics; stdout is not authoritative.
- **Exit code zero without the required artifacts is a failure.**

## 8. Requalification triggers

Re-run the affected task class when any of these changes: model slug or version;
provider; provider privacy or retention policy; prompt; fixture; output schema;
orchestration harness; tool configuration; Home Assistant version; the
authorization implementation; the capability standard; or after a material
production incident or missed escalation.

Requalification is **not calendar-driven**. A periodic audit exists only to
catch drift that went unreported, and finding drift there is a signal that a
trigger was missed.

## 9. Fail-closed behavior

- If every candidate fails, record **no qualified winner**. Do not weaken a gate
  to fill a slot.
- An incumbent route survives only by clearing the current suite on unchanged
  inputs. Otherwise disable the route, or require human approval for a temporary
  assignment.
- Schema-invalid output is a failed attempt, not a formatting nit.
- Fixture-hash drift blocks comparison outright.
- An interrupted trial may resume from recorded inputs; partial data can never
  select a winner.
- Budget exhaustion stops the run and records an incomplete result. The limit is
  never raised automatically.
- If Notion is unavailable, publish the Git artifacts and mark synchronization
  pending.

## 10. Monthly cycle

**Cadence:** 09:00 ET on the first Tuesday of each month; the next business day
if that is a U.S. federal holiday. The cycle retests routing for the fixed task
classes and for the most-used and every security-sensitive prompt.

### 10.1 Prerequisites

| Requirement | Verify with | Blocks the run |
|---|---|---|
| Approved run manifest with token and dollar limits | `make ai-qualification-preflight` | Yes |
| OpenRouter access and provider metadata | preflight | Yes |
| Sanitized HA fixtures with matching stored hashes | preflight | Yes |
| Git registry integrity | `make prompt-ledger-validate` | Yes, for publication |
| An isolated worktree per writing agent | orchestrator records path and branch | Yes |
| Notion connection | read the Prompt Ledger database | No; mark sync pending |

### 10.2 Steps

| Step | Action | Record |
|---|---|---|
| 1 | Snapshot the catalog, providers, and prices | dated snapshot plus hash |
| 2 | Filter on privacy, pinning, tools, context, availability, lifecycle | exclusion ledger |
| 3 | Reuse matching records; one bounded trial per survivor | screening data |
| 4 | Full suite for those that clear; repeat finalists three times | comparable evidence |
| 5 | Apply gates, compute expected cost, propose assignments | routing decision |
| 6 | Refactor a prompt only where measured results support the edit | new prompt version |
| 7 | Validate Git artifacts, check pointers, sync Notion, publish the report | commits and findings |

### 10.3 What a cycle may change without amending this document

A cycle may change **assignments, prompt wording, and prompt status**. Amend
this standard only for a policy change. Supersede the ADR only if the decision
*method* changes. Update the runbook when operator steps change. Routine results
must not cause document churn.

## 11. Ownership and exceptions

The AI PM role owns the schedule, the registry, and the report. The orchestrator
prepares isolated worktrees and produces scoped commits. A **human approves**
exceptions, merges, and any live deployment.

An exception is recorded in the run artifact under `exceptions[]`, and each entry
carries four fields, all required:

| Field | Meaning |
|---|---|
| `owner` | The named person accountable while the exception is open. A **role** owns this document; a **person** owns an exception, because a deviation needs somebody to answer for it. |
| `reason` | What the exception permits, and why the standard's default is wrong here. |
| `expires` | An absolute date (`YYYY-MM-DD`) or a named event (`"when MQ-F1 closes"`). Never a duration, never "temporary". |
| `approved_by` | The human who approved it. An agent cannot approve its own exception. |

An exception missing any of the four is void, and the run is treated as having no
exception at all. An exception with no expiry is a policy change and belongs in a
revision of this document, reviewed as such.

**A task class with no qualified winner does not get an implicit exception.** Its
route is disabled. Substituting a model qualified for a *different* task class is
the exact move this rule forbids, because that model's evidence says nothing
about the task it would be doing. A temporary assignment requires its own
`exceptions[]` entry with all four fields.

Live customer systems and production credentials are outside this process.

## 11.1 The boundary is not production-proven

No document, proposal, PR body, or customer commitment may describe the occupant
authorization boundary as proven, verified, or production-ready until the lab
tenant-token negative tests in
[`MQ-F1`](../tasks/Tasks-Model-Qualification-Followups.md) have passed.

A qualification result is evidence about a **model**, not about a deployment. A
model reading pinned source correctly shows what the code says. Whether a tenant
token can actually reach `hassio.*` or `shell_command.*` on a running instance is
a runtime property, and only a live negative test settles it. Treating a model's
correct reading as proof of the boundary is the single most likely way this work
gets misused.

## 11.2 Both review layers are required

A review gate runs **deterministic checks and model review, and neither
substitutes for the other.** This is not a preference; it is what the first
cycle measured.

Across four review rounds, three qualified models read the same two documents
and none of them noticed a link that resolved nowhere. They objected to link
*style* while the broken link sat in the same section. `markdown-link-check`
found it in under a second.

The division is stable, so encode it rather than rediscover it:

| Layer | Finds | Cannot find |
|---|---|---|
| Hooks, schemas, link checks, hash verification, tests | A path that does not exist, a schema a payload violates, a hash that moved, a secret in a prompt | Whether a claim is true, whether a prerequisite is missing, whether a rollback would work |
| Model review | Unstated assumptions, aspirational claims, missing failure paths, meaning | Anything requiring the filesystem, the network, or arithmetic it cannot perform |

Therefore: run the mechanical checks **before and after** every model review
round. A model review that passes while `make validate` is red is not a passing
review. A green mechanical run with no model review has checked syntax, not
sense.

## 12. Tripwires

This standard is being violated, or has gone stale, if any of these is true.

- A route is cited with **no run artifact**, or the artifact does not name the
  provider that served it.
- A qualification result is reused across a **changed prompt, fixture, schema,
  or harness version**.
- A winner was selected on price **before** the privacy and provider gates ran.
- A gate was **relaxed** to produce a winner where a run had none.
- Ground truth appears **inside a prompt file**, which makes every score since
  meaningless.
- The secret scanner was **loosened** to let a fixture through.
- Reasoning effort **above `high`** appears in a recorded trial.
- A security-critical route is served by an **auto, fused, or alias** slug.
- The occupant authorization boundary is called **proven** anywhere while MQ-F1
  is still open.
- A Task B result is relied on from `main` while
  `HA_OCCUPANT_CONTROL_STANDARD.md` is still unmerged.
- A task class with no qualified winner is quietly served by a model qualified
  for a **different** task class, with no `exceptions[]` entry.
- The rework constant in §6.4 is still the default assumption after 2027-07-30,
  or is being reported anywhere as if it were measured (tracked as MQ-F5).

## 13. Related

- [`ADR-task-class-model-routing.md`](../adr/ADR-task-class-model-routing.md) — the decision method.
- OpenRouter cycle runbook (`docs/runbooks/openrouter-model-qualification.md`) — how to run a cycle. Carried as PR B scope; not part of this governance contract.
- [`MODEL_EVALUATION_GOVERNANCE_STANDARD.md`](MODEL_EVALUATION_GOVERNANCE_STANDARD.md) — external-benchmark inputs for role assignment.
- [`ADR-model-router-control-plane.md`](../adr/ADR-model-router-control-plane.md) — where routing policy lives and who may change it.
- `docs/standards/HA_OCCUPANT_CONTROL_STANDARD.md` **(not yet on `main`)** — the classification authority Task B is scored against. It is unmerged, on branch `feat/commissioning-contract-closure` at commit `25ce339`. Until that branch lands, a reader on `main` cannot open it, and this standard's Task B scoring rests on a document that is not yet published. Treat that as a merge dependency, not a broken link.
- [`agent-config/prompt-ledger.yaml`](../../agent-config/prompt-ledger.yaml) — the canonical prompt registry, in this repository.
- `docs/templates/model-qualification-result.schema.json` — the run artifact contract. Carried in PR B; historical 1.x runs validate against `model-qualification-result.v1.schema.json` (frozen in PR A).
- [`docs/tasks/Tasks-Model-Qualification-Followups.md`](../tasks/Tasks-Model-Qualification-Followups.md) — the bounded follow-up work this standard's open defects opened.

## Evidence status

Home Assistant claims in the Task A fixture are verified against
[Core 2026.4.2 automation source](https://github.com/home-assistant/core/blob/2026.4.2/homeassistant/components/automation/__init__.py#L775-L870)
at commit `f886b03e140bf23d5ba0f9f3556bc9e0cd2cd9a2`, and against the stored
excerpt hashes in `tests/fixtures/model_qualification/ha_2026_4_2/MANIFEST.json`.

OpenRouter availability and prices are dated observations from the
[`/api/v1/models`](https://openrouter.ai/docs/guides/overview/models) response,
not commitments by the provider.

The rework constant in §6.4 is an assumption. The Stage 2 one-model-per-family
economy is a recorded coverage limitation. Runtime reachability of any service
by a tenant token is unproven until the live negative tests run.

Two open defects from the first cycle are recorded in
`artifacts/model_qualification/runs/mq-20260730-003/KNOWN_DEFECTS.md` rather
than patched mid-cycle: a false positive in the Task B invention detector on
rule references, and Stage 1b's inability to predict a completion-time routing
rejection. Both are queued as requalification triggers. Editing ground truth
after seeing results would void every score taken with it, so it is not done.

## Revision

| Date | Version | Change |
|---|---|---|
| 2026-07-30 | 0.1.1 | Documentation reliability review (`dr-20260730-001`, `-002`) closed nine findings: exception entries now require owner, reason, absolute expiry, and human approver; §11.1 forbids calling the occupant authorization boundary production-proven while MQ-F1 is open; the rework constant gained an owner, a closing condition, and an absolute backstop; relative dates replaced with absolute ones; and a link to `HA_OCCUPANT_CONTROL_STANDARD.md` that resolves nowhere on `main` is now recorded as an unmerged merge dependency rather than a working reference. Zero critical findings at HEAD. |
| 2026-07-29 | 0.1 | Initial standard. Establishes task-class qualification against bounded RyzaLab fixtures, quality-floor-first selection with cost deciding among survivors, whole-catalog consideration with machine-readable exclusions, privacy and pinning gates ahead of price, four-stage qualification, expected completion cost including retries and rework, per-task-class winners with no overall winner, trigger-driven requalification, fail-closed no-winner handling, and the monthly cycle with its two blocking preflight commands. Records the asymmetric gate construct for capability classification and the Codex file-producing lane. |
