# Standard — Agent Runtime & Source-Visibility Model (cross-agent)

**Status:** Active (v1.0, 2026-07-10)
**Risk Tier:** Confirm (changes how every agent decides what it can see and trust)
**Audience:** **Every** agent surface operating on any RyzaLab work — ChatGPT Projects, claude.ai, Claude Code (local WSL + cloud VM), Codex CLI, Cursor. This is a cross-agent standard, not a ChatGPT-only rule.
**Home:** `surencio/ryzalab-platform` (cross-customer SSOT). Consumed by customer repos via `PLATFORM_VERSION` + `docs/UPSTREAM/` mirror. Indexed from [`agent-config/CLAUDE.md`](../../agent-config/CLAUDE.md).
**Surface adapters:** [`agent-config/CHATGPT_PROJECTS.md`](../../agent-config/CHATGPT_PROJECTS.md) · [`agent-config/AGENTS.md`](../../agent-config/AGENTS.md) (Codex) · [`agent-config/.cursorrules`](../../agent-config/.cursorrules) (Cursor). Each adapter maps this standard to its surface; none may contradict it.

> **Why this exists.** Runtime/source-visibility rules were first written for ChatGPT Projects ("Project files", "Project chat history", "saved memory", "scheduled tasks are self-contained"). Landed verbatim, those constructs *mislead* a repo agent: a Codex CLI session has no "Project Knowledge", a Claude Code cloud VM has no local WSL files or secrets, GitHub Actions cron *can* read the checkout. This standard defines one universal source model and one per-surface visibility matrix, so every agent reasons about what it can actually see — and never claims a source it did not use.

---

## 1. The four runtime-mode questions (ask before any meaningful task)

Classify the runtime before acting. State only the assumptions that materially change the answer.

- **Memory mode** — which memory applies: none · this surface's saved/auto memory · repo-committed memory · user-provided context only. Memory is *background*, never source-of-truth for current state (§4).
- **Source mode** — which source classes are actually visible **on this surface right now** (§3 matrix). Do not imply access to a class marked "not visible" for your surface.
- **Reasoning level** — higher reasoning only when justified (strategy, architecture, multi-step synthesis, source reconciliation, risk review, durable decisions). Normal reasoning for edits, summaries, formatting, routine classification.
- **Task mode** — one-time answer · artifact update · source audit · scheduled/background job · connector action · web-grounded research · implementation handoff.

## 2. Universal source classes

Every input an agent uses belongs to exactly one class. The class — not the surface's local vocabulary — determines trust.

| Class | What it is |
|---|---|
| **Current prompt / chat** | The active conversation text and its inline attachments. |
| **Repo checkout** | The working tree the agent can read/edit (local WSL clone, cloud-VM clone, IDE workspace). |
| **Pinned platform mirror** | `docs/UPSTREAM/` at the tag in `PLATFORM_VERSION` — the authoritative offline copy of cross-customer governance. |
| **Agent memory** | This surface's persistent memory: Claude auto-memory index, Codex memory (`~/.codex/memories/MEMORY.md`), repo-committed memory files. |
| **Surface-provided knowledge bundle** | Files a UI injects: ChatGPT Project Knowledge, claude.ai project files/attachments. **Surface-specific — does not exist on CLI/IDE surfaces.** |
| **Connector / MCP data** | Live private sources reached via a connector: Notion, Gmail, Drive, GitHub, Slack, ha-mcp. Authoritative only for the data the connector exposes at runtime. |
| **Web** | Browsing / search. Required for facts that change: prices, docs, releases, laws, schedules, product behavior. |
| **Shell command output** | Live output of a command the agent ran. Highest-confidence evidence for *current system state*. |
| **IDE / editor state** | Open files, selection, diagnostics — visible only to IDE-embedded surfaces. |
| **Scheduled / background payload** | The self-contained inputs handed to a cron/routine/GitHub-Action run. See §5. |

## 3. Per-surface visibility matrix

`Y` = visible · `N` = not visible · `~` = conditional (only if explicitly attached/enabled/invoked; verify before relying).

| Source class | ChatGPT Projects | claude.ai chat | Claude Code (local WSL) | Claude Code (cloud VM) | Codex CLI | Cursor |
|---|---|---|---|---|---|---|
| Current prompt / chat | Y | Y | Y | Y | Y | Y |
| Repo checkout | N | N (attachments are snapshots, not a checkout → bundle) | Y | Y (from GitHub, not your machine) | Y | Y |
| Pinned platform mirror | N | N (unless attached; then a snapshot, not a verifiable mirror) | Y | Y | Y | Y |
| Agent memory | ~ (saved memory) | ~ (saved memory) | ~ (Claude auto-memory if configured) | N (fresh VM) | Y (`~/.codex` memory) | ~ |
| Surface knowledge bundle | Y (Project Knowledge) | ~ (attached project files) | N | N | N | N |
| Connector / MCP | ~ (enabled connectors) | ~ | ~ (configured MCP) | ~ (scoped proxy) | ~ (sandbox may block network) | ~ (MCP/IDE) |
| Web | ~ (browsing on) | ~ | ~ | ~ | ~ | ~ |
| Shell command output | N | N | Y | Y | Y | Y |
| IDE / editor state | N | N | ~ (VS Code ext) | N | N | Y |
| Scheduled / background payload | self-contained only (§5) | — | — | — | — | — |

*Interactive-session rows only; the "scheduled / background payload" row is n/a for interactive surfaces — a scheduled job classifies its own runtime under §6. "Repo checkout" on claude.ai is `N` because an uploaded file is a point-in-time snapshot under the current prompt / knowledge bundle, not a working tree with git/path/shell semantics.*

**Load-bearing reads of this matrix:**

- **Codex CLI / Cursor / Claude Code have NO surface knowledge bundle.** Never assume uploaded ChatGPT Project Knowledge is available on a CLI/IDE surface.
- **Claude Code cloud VM has NO local WSL files, secrets, or auto-memory.** It clones from GitHub and returns changes via PR ([`agent-config/CLAUDE.md`](../../agent-config/CLAUDE.md) § Trunk policy #9). Do not assume local `/home/ryang` paths or `~/.config/ryzalab/secrets*.env` exist there.
- **Codex `workspace-write` may have no outbound network** — connector/web reads can silently fail ([`agent-config/AGENTS.md`](../../agent-config/AGENTS.md) § Sandbox networking).
- **Do not claim a source was checked unless it was visible AND used.**

## 4. Cross-agent freshness rule

**Age is a risk signal, not an automatic archive rule.** A file being older than 2 months means *verify before relying*, not *discard*.

The following **override** a generic age heuristic and stay authoritative regardless of age:

- **Living indices** — the Claude auto-memory index and Codex memory index are continuously maintained continuity state.
- **Pinned platform mirror** — `docs/UPSTREAM/` at `PLATFORM_VERSION` is authoritative by contract, not by date.
- **Committed standards / ADRs marked `Active` or `Accepted`** — a dated standard is current until superseded, not until 60 days pass.
- **Live command / connector output** — reflects the system *now*.

Only genuinely superseded, `Draft`-abandoned, or explicitly-archival material is stale. When in doubt, verify against a higher-trust class (shell output > pinned mirror > committed standard > memory) rather than archiving.

## 5. Memory is not source-of-truth (three fenced rules)

Recalled memory is background context reflecting what was true when written. It never overrides current source files or live state. Three rules that agents have gotten wrong:

1. **`MEMORY.md` archival rule is surface-scoped.** *"ChatGPT Project Knowledge files named `MEMORY.md` are archival snapshots unless the ChatGPT active source index marks them current. This does NOT apply to Claude auto-memory, Codex memory (`~/.codex/memories/MEMORY.md`), repo-committed memory files, SSRP logs, or live Work Log / Backlog / QA Log state."* Archiving a living index by filename or age destroys active RESUME/SSRP continuity.
2. **"Project files" is surface-specific vocabulary.** In a cross-agent context, say **"surface-provided knowledge bundle"** and map it per §3. A CLI/IDE agent that reads "Project files are visible" and assumes an uploaded bundle exists is wrong.
3. **Scheduled-task self-containment is ChatGPT-specific.** *"ChatGPT scheduled tasks cannot read ChatGPT Project Knowledge unless it is included in the task payload; other schedulers (GitHub Actions cron, Claude routines) follow their own checkout/runtime contract."* A GHA cron **does** read the checked-out repo and the pinned mirror — see §6.

## 6. Scheduled / background jobs: self-containment contract

A scheduled or background job inherits only what its runtime contract provides — not a chat's context, not a UI's uploaded bundle.

- **ChatGPT scheduled tasks:** self-contained. The task prompt must embed everything: source locations/URLs to check, decision rules, definition of "material change", output format, standing constraints, escalation/ignore criteria. Write it so it would still work pasted into a fresh chat with no Project context.
- **GitHub Actions cron / Claude routines:** self-contained *at the code level*, but **do** get the repo checkout + pinned mirror. They read files; they do **not** inherit an interactive session's memory or a UI's uploaded bundle. Pass event inputs via validated env, never inline into shell (injection-safe), matching [`.github/workflows/governance-digest.yml`](../../.github/workflows/governance-digest.yml).

The automated staleness audit ([`scripts/staleness_audit.py`](../../scripts/staleness_audit.py), [`.github/workflows/staleness-audit.yml`](../../.github/workflows/staleness-audit.yml)) is an example implementation of a self-contained, read-only, advisory background job under this contract.

## 7. Enforceability scope (do not overclaim)

This standard is **policy consumed by agents**, plus one **advisory** automated check (the staleness audit). It is *not* a runtime sandbox:

- It cannot force a surface to reveal a source it hides, nor prove an agent didn't hallucinate a source. That relies on agent-config policy + review + the SSRP Work Log audit, not a static check.
- The staleness audit flags *candidates* by header/age/supersession heuristics; a human or a review agent adjudicates. It does not auto-archive or auto-edit.
- The per-surface matrix is a **default** contract; a specific session may differ (a connector disabled, browsing off). Verify, then state the assumption.

## 8. Consequences

**Positive:** one source model every agent shares; no ChatGPT-only silo; per-surface truth prevents the "assumed a source I don't have" failure; freshness rule stops living-memory destruction; a self-contained scheduled-job contract; an advisory audit that catches drift by exception.

**Negative / cost:** a new standard to version; surface adapters must be kept pointing here; the matrix must be updated when a new surface or connector is added (the staleness audit watches this file too).

**Neutral:** SSRP (C1–C7), Risk Tiers, and the qa-lens gate are unchanged.

---

**Last reviewed:** 2026-07-10.
