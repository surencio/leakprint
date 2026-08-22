# Standard — Agent Dispatch Isolation

**Status:** DRAFT (template landed; `[MEASURED]` rows pending V-run — see §6)
**Risk Tier:** Confirm (changes how every agent dispatches Codex)
**Program alignment:** [AI Ops Operating Model](../../AI_OPS_OPERATING_MODEL.md) — agent-ops reliability control. Prerequisite for gap **G6** (subagent-execution proof), not its resolution.

> Claim-maturity tags: **[MEASURED]** = observed; **[TARGET]** = acceptance bar; **[HYPOTHESIS]** = expected, unproven.

## 1. Why this exists

Multiple Claude orchestrator sessions in one WSL2 account each dispatch `codex exec`. They share mutable SQLite state in `~/.codex` (`logs_2.sqlite` ~189 MB + `-wal`/`-shm`, `state_5`, `goals_1`, `memories_1`). SQLite serializes writers, so **a second concurrent dispatch blocks to timeout** [MEASURED 2026-06-22]. Worse, a broad `pkill -f "codex exec"` from one session **destroys sibling sessions' work** [MEASURED]. Both are agent-ops reliability failures: contention timeouts get misread as task failures and pollute the confab/false-done signal the operating model measures.

## 2. The rule (all agents)

1. **Never run `codex exec` (or `gemini`) directly for dispatch.** Use `scripts/codex_dispatch.sh` — the one blessed launcher. CI enforces this (`scripts/check_dispatch_isolation.py`).
2. **Never kill by name** (`pkill -f`, `kill -9 … -f`). Stop a dispatch via `codex_dispatch.sh stop <D>` (process-group + cmdline-verified).
3. **Concurrent work runs in an isolated home.** Serialized/resumable work → session root; any concurrent job → `--concurrent` (per-dispatch child home). `--concurrent` dispatches are **not resumable** (child home is reaped on success) — never `codex resume` one.
4. **Skills off by default.** `~/.codex/skills` is 558 symlinks; review/QA dispatches don't need them. Opt in with `--with-skills` only when the task depends on skill instructions.

> **Scope & limits (honest).** This standard isolates **SQLite contention, not privilege.** Per the
> topology below, `auth.json`/`config.toml` are symlinked to a SINGLE shared Codex identity and
> dispatches run `--sandbox workspace-write` — so a dispatch is **not** a privilege/secret boundary
> (a read-only sandbox for review/QA dispatches is a tracked follow-up). And the CI lint
> (`check_dispatch_isolation.py`) enforces the rule only against **committed** `.sh/.py/.yml` files; an
> orchestrator issuing `codex exec` via its runtime Bash tool is not statically detectable — that path
> relies on agent-config policy + review, not CI.
>
> **Prose may name a forbidden command.** The lint scans code, not documentation: `*.md` is out of
> scope (defect D-04), and inside `.py` the file is parsed with `ast` so docstrings — and any other
> bare string statement — are excluded (defect D-04b). Explaining in a docstring *why* `pkill -f` is
> banned is not a violation of the ban. What is still scanned: every string that a call can execute,
> because a shell command in Python is a string argument. `tests/test_dispatch_isolation.py` pins
> both halves — the prose exemption and the detection it must not weaken.

## 3. Home topology

```
~/.codex-sessions/<S>/                 # session root (stable; resume lives here)
  auth.json -> ~/.codex/auth.json      # symlink: single identity (shared by design)
  config.toml -> ~/.codex/config.toml  # symlink: single-source config
  skills/ -> ~/.codex/skills           # OPTIONAL (--with-skills only)
  sessions/ logs/ state/...            # PRIVATE to S
  dispatches/<D>/                      # per-dispatch child home (concurrent jobs)
    auth.json/config.toml symlinks; own sessions/logs/state; pid/pgid/cmd
  failed_dispatches/<D>/               # retained on non-zero exit (debugging)
```

- `<S>` = SSRP Session ID (`{agent_short}-YYYYMMDD-{4hex}`); `<D>` = `dispatch-{4hex}`.
- Auth/config are **symlinks** (single identity, single-source config). Only the contended DBs are isolated per home.

## 4. Launcher interface

```
codex_dispatch.sh run      --session <S> [--concurrent] [--with-skills] [--timeout 300] -- "<prompt>"
codex_dispatch.sh stop     <D>
codex_dispatch.sh validate <D>          # V4 write-isolation check
codex_dispatch.sh gc       [--days 7]   # reap stale homes (liveness-checked)
```

Load-bearing behaviors (CI/code-review must assert all):
- own **process group** (`setsid`); `stop` = `kill -- -$PGID` after verifying live cmdline matches recorded `cmd` (PID/PGID-recycle guard); never `pkill -f`.
- `timeout -k 15 <n>` (SIGKILL fallback on hung I/O).
- **retain-on-failure:** prune `<D>` on exit 0; move to `failed_dispatches/<D>` otherwise.
- **symlink integrity:** after run, assert `auth.json`/`config.toml` are still symlinks; if an atomic-rename replaced one, copy the refreshed payload to canonical and restore the symlink.
- MCP: no port/socket collision between concurrent dispatches.
- `gc`: delete only homes whose recorded PID is dead.

## 5. Scratch hygiene

Temp handoff artifacts (task prompts, review outputs, run logs) live in `/tmp`, never committed; the creating agent deletes them once consumed — **except** failed-dispatch evidence, which is retained under `failed_dispatches/`. See `agent-config/CLAUDE.md` § Scratch & handoff-artifact hygiene.

## 6. Validation status ([MEASURED] pending — fill after V-run)

| Check | Bar | Result |
|---|---|---|
| V1 control (shared home blocks) | ≥1 stall/timeout reproduced | _pending_ |
| V2 treatment (isolated, concurrent) | `Time(concurrent) ≤ Time(solo)×1.1 + 5s` | _pending_ |
| V3 identity (symlink auth/config) | `codex login status` ok; symlinks intact | **[MEASURED] partial — ok 2026-06-22** |
| V4 write-isolation | all `~/.codex/*.sqlite*` (incl `-wal`/`-shm`) unchanged by SHA256 | _pending — v0.2 check was WAL-blind, corrected_ |
| V5 orphan check | no processes left in dispatch PGID after stop | _pending_ |

> V-runs require a quiesced window (no sibling Codex sessions) and a backup of `~/.codex/*.sqlite*` before V1 (the 189 MB WAL can corrupt under forced kill).

## 7. Revision

| Date | Version | Note |
|---|---|---|
| 2026-06-22 | DRAFT (spec v0.3) | Template landed; process-group teardown, symlink-restore, retain-on-failure, WAL-aware V4, scoped CI lint folded from AGY review. |
| 2026-08-08 | DRAFT (spec v0.3.1) | D-04b: the CI lint parsed `.py` docstrings as code, so prose naming a banned command failed the build (15 consecutive red commits on main). Docstrings are now excluded via `ast`; executable string arguments are not. Scope note added above. |
