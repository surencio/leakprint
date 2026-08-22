# Access Management Standard

**Status:** Active
**Owner:** RyzaLab operator (Ryan Surencio)
**Audience:** Operator + any agent making access-related changes (Cursor, Claude Code, Codex)
**Scope:** How RyzaLab reaches a customer's Home Assistant for maintenance and commissioning, where credentials live, and how the operator path stays usable when Tailscale or YAML is broken.

This is policy. It is intentionally short. Runbooks (`tailscale-hardening.md`, `CUSTOMER_IMPLEMENTATION_PLAYBOOK.md`, `CREDENTIAL_RECOVERY_PACKET_TEMPLATE.md`) carry the procedural detail and link back here.

---

## 1. Why this exists

A repeatable, low-blast-radius operator path across all RyzaLab customer Home Assistants. Without one written rule, drift happens fast: inconsistent Tailscale names, "operator service account" used loosely, secrets mixed across customers, and no rollback ladder when the primary path breaks.

This document is also the explicit deferral note for two things RyzaLab is **not** building yet: a multi-tenant access portal, and a central log/observability database. Triggers for revisiting both are defined in §10 and §11.

---

## 2. Operator identity: `ryzalab_support`

### 2.1 Canonical name

Every customer HA documents a single operator-facing user named **`ryzalab_support`**. This replaces any prior reference to "operator service account," `ryzalab_admin`, or informal naming in repo docs and runbooks.

- `ryzalab_support` is the **maintenance** identity, not the customer's owner account.
- The customer's owner account is theirs and is documented in the credential recovery packet — RyzaLab does not co-own it.
- `root` over SSH on port 2222 is host/OS access (a separate axis); `ryzalab_support` is the HA user inside the application.

### 2.2 Privilege reality (read this honestly)

Home Assistant's permission model is coarse. Most tools we rely on for maintenance — `ha-mcp` write paths, entity renames, service calls on restricted entities, supervisor operations, config edits — require an **admin-flagged user**. Marketing this account as "non-admin" understates the blast radius and creates a false security claim.

Standard:

| Operator activity | `ryzalab_support` role | Token type |
|---|---|---|
| Live maintenance via ha-mcp / scripts (rename, service call, restart) | Admin | Per-site LLT, used during maintenance window only |
| Read-only diagnostics (state inspection, template eval, search) | Admin (same user) | Same per-site LLT |
| Customer family / dashboard access | N/A — customer family uses owner + per-person accounts | N/A |

We do **not** maintain a separate "non-admin support account" because the maintenance work the account exists to do requires admin. Reduce blast radius via the other levers below (per-site unique tokens, Tailscale ACL scoping, rotation contract, no on-appliance ha-mcp) — not via a privilege claim we cannot enforce.

If HA later ships a finer-grained permission model that lets `ryzalab_support` be non-admin while still doing maintenance, this section is the trigger to revisit.

### 2.3 Per-site `ryzalab_support` provisioning

Created during bench build (Phase 1) before site goes live. See `CUSTOMER_IMPLEMENTATION_PLAYBOOK.md` Phase 1 / Gate 2 for the checklist row.

---

## 3. Remote addressing: Tailscale

### 3.1 Naming standard

- **Tailscale machine name:** `ha-[sitecode]` (lowercase, hyphenated). Examples: `ha-par`, `ha-hou`, `ha-aus`.
- **SSH config alias:** `ha-[sitecode]` (matches machine name).
- Generic Tailscale names (`homeassistant-1`, etc.) are not acceptable for RyzaLab-managed sites.

### 3.2 URL pattern

| Path | Pattern |
|---|---|
| HA Web UI (remote, MagicDNS) | `https://ha-[sitecode].[tailnet].ts.net:8123` |
| HA Web UI (remote, Tailscale IP fallback) | `https://[100.x.y.z]:8123` |
| HA Web UI (local LAN) | `http://homeassistant.local:8123` |
| SSH (operator) | `ssh ha-[sitecode]` (port 2222 via SSH config) |

The `*.ts.net` MagicDNS suffix exposes the tailnet identifier in URLs and bookmarks. This is acceptable risk at current scale. Document the pattern in repo; record the *filled-in* URL only in the vault and the credential recovery packet.

### 3.3 Tailscale ACLs

Operator reach is scoped via Tailscale tags so that even if the operator laptop is compromised, the network reach is limited to RyzaLab-managed customer hosts on their HA service ports. See **Appendix A** for the canonical ACL stanza.

Audit the deployed ACL against Appendix A any time a new customer site joins the tailnet.

---

## 4. Secrets governance

### 4.1 System of record

**Proton Pass is the single source of truth** for per-site operator credentials. One vault item per customer site, with these fields:

- `site_code` (e.g. `par`)
- `ha_base_url` (full MagicDNS URL with port)
- `ha_tailscale_ip` (`100.x.y.z` fallback for WSL with `--accept-dns=false`)
- `ssh_host` (e.g. `ha-par`)
- `ryzalab_support_password`
- `ryzalab_support_llt` (per-site long-lived access token)
- `created` / `last_rotated` dates

**No parallel SoT.** Encrypted spreadsheets, Notion pages, email, and shared drives are explicitly **not** acceptable as a credential store. If you need a cold backup, use Proton Pass's encrypted-export feature into RyzaLab-controlled storage. Two SoTs always drift; pick one and enforce it.

### 4.2 Bitwarden / KeePassXC alternative

If RyzaLab moves off Proton Pass, the chosen replacement must (a) support per-item custom fields, (b) support emergency access / continuity contact, and (c) live outside the customer network. Vault choice does not change anything else in this standard.

### 4.3 secrets.env on the operator laptop

Local convenience copy only. Rules:

- One file **per site**: `~/.config/ryzalab/secrets-[sitecode].env`. Source the one for the customer you are working on; never source two at once.
- Never committed. Path is in `.gitignore`. Treat any commit attempt as an incident.
- Rotated whenever the per-site LLT rotates. Proton Pass is the canonical copy; `secrets.env` is the disposable mirror.
- See **Appendix B** for the file template.

Prefixed-variable patterns (`HA_TOKEN_PAR`, `HA_TOKEN_HOU` in one file with wrapper scripts that switch) are explicitly **not** the standard. Per-site files mean a wrong-customer accident requires sourcing the wrong file, which is a more visible mistake than calling the wrong wrapper.

### 4.4 What is not stored anywhere

The customer credential recovery packet **never contains the `ryzalab_support` password**. The packet covers owner credentials only. The packet may include one informational line stating that RyzaLab uses a dedicated maintenance account; the packet template carries the canonical wording.

### 4.5 Operator cross-site credentials (distinct from per-site)

Some operator credentials are **not per-site** — they're operator infrastructure that touches every customer's coordination plane. Examples:

- `NOTION_TOKEN` — used for SSRP discipline writes against Plane 8 databases (Work Log / Backlog / QA Log) which span all customers. Not tied to any one site's HA appliance.
- `GITHUB_TOKEN` — used for cross-repo `gh api` calls against `surencio/ryzalab-platform`, all customer repos, and `surencio/ryzalab-notion-mcp`. Not tied to any one site.
- `CLOUDFLARE_API_TOKEN` (when `ACCESS_MANAGEMENT_STANDARD §9.4` Layer B Cloudflare Tunnel is operational) — operates the per-site tunnels but the token itself is operator-level, not site-level.
- Vault provider API tokens (Proton Pass / Bitwarden / etc.) — operator-level by definition.

**Storage:** these credentials live in a designated **operator-cross-site** secrets file, **distinct from per-site files** in §4.3:

```
~/.config/ryzalab/secrets-operator.env
```

This file is **not** a substitute for per-site `secrets-[sitecode].env`; it's a sibling with different rotation triggers and different blast radius. Sourcing it is permitted in any operator shell (cross-site work like releasing a platform version, writing a cross-customer Notion Backlog row, opening an issue across repos).

**Rules:**

1. **Never** put per-site credentials in `secrets-operator.env`. `HA_TOKEN`, `HA_BASE_URL`, `SSH_HOST` belong in per-site files only.
2. **Never** put operator-cross-site credentials in per-site files. Duplicating `NOTION_TOKEN` across `secrets-par.env`, `secrets-aus.env`, etc. produces stale copies that silently break tooling (observed 2026-04-28: `secrets-willr.env`'s `NOTION_TOKEN` was 401-invalid while `secrets-arcadia.env`'s was valid because rotations weren't propagated).
3. **Two-axis rotation:** per-site credentials rotate on per-site triggers (offboarding, suspected per-site compromise — see §6). Operator-cross-site credentials rotate on operator-level triggers (operator endpoint loss, suspected platform-account compromise, vault provider notification, annual cadence).
4. **Vault is still SoT** (per §4.1). `secrets-operator.env` is the disposable laptop mirror; the canonical copy lives in Proton Pass under a separate vault item labeled `RyzaLab Operator (cross-site)`.
5. **Sourcing pattern:** `source ~/.config/ryzalab/secrets-operator.env` first if you need cross-site creds; then optionally source one site's file if you also need per-site access. The wrong-customer P0 rule still applies — source at most one per-site file per shell.

**File template (for `secrets-operator.env`):**

```bash
# ~/.config/ryzalab/secrets-operator.env
# DO NOT COMMIT. Mirror of the Proton Pass entry "RyzaLab Operator (cross-site)".
# Rotation triggers: operator endpoint loss, suspected platform-account compromise,
# vault provider notification, annual backstop. NOT site-level — site-level rotations
# do not touch this file.

export NOTION_TOKEN="[Notion integration token, scope: Work Log + Backlog + QA Log DBs]"
export GITHUB_TOKEN="[gh PAT, scope: repo + workflow + read:org]"
export CLOUDFLARE_API_TOKEN="[CF API token for Tunnel + Access management; populate when §9.4 Layer B is deployed]"
```

**Migration triggers — when this section becomes load-bearing:**

The current operator setup (as of 2026-04-29) has `NOTION_TOKEN` duplicated across per-site files, which violates rule #2. Migration steps:

1. Create `secrets-operator.env` from one canonical Proton Pass entry.
2. Strip `NOTION_TOKEN` (and any other cross-site creds) from `secrets-[sitecode].env` files.
3. Update operator muscle memory: source `secrets-operator.env` for cross-site work; source per-site only when working on that one site.
4. Document the migration in Notion Work Log with `secrets-rehome` tag.

This migration is **mandatory before**: the first paid SLA customer onboarding, OR `N≥3` customer sites, OR first suspected cross-site credential compromise — whichever fires first. Until then, the duplicated state is acceptable but tracked as technical debt in `docs/tasks/Tasks-Business-Continuity.md` BC-7 (added in `v0.1.0`).

### 4.6 Agent raw-value access: `agent_raw_access` and `approved_consumers`

Added 2026-08-19 after an incident: an agent ran `ryzalab-secret get NOTION_TOKEN | head`, and `head` — an ordinary output-producing utility, not a logger — printed the value into a transcript. §4.1–4.5 govern where a credential's *location* lives and how a human resolves it; this section governs whether an **agent** may resolve a given credential to its raw value at all.

**The gate.** `scripts/credential_registry.json` entries may carry two additional fields:

- `agent_raw_access` (bool, default `true`) — when `false`, `ryzalab-secret get`/`run` refuse the call for any caller not listed in `approved_consumers`, before `pass-cli` is ever invoked. `check`/`list` are never gated — they are metadata-only and never emit a value.
- `approved_consumers` (list of repo-relative script paths) — the only callers exempted from the refusal above.

**Enforcement.** `scripts/ryzalab_secret.py:_caller_is_approved()` requires three independent facts about the direct parent process, all must hold:

1. **Identity.** `/proc/<ppid>/exe` — a kernel-maintained pointer to the actual executable inode backing the process, not caller-supplied data — resolves to the same Python interpreter binary this process itself runs under (`sys.executable`).
2. **Isolation.** `argv[1]` (from `/proc/<ppid>/cmdline`) is literally `-I` — Python's isolated-mode flag, which disables `site.ENABLE_USER_SITE` and ignores `PYTHONPATH` for that process from interpreter startup onward.
3. **Argument.** `argv[2]` resolves — following symlinks, discarding `..`/relative tricks, and resolving a relative path against the parent's *real* cwd (`/proc/<ppid>/cwd`), never this process's own cwd — to the exact canonical absolute path of one of `approved_consumers`.

An unreadable parent, or a candidate that fails any of the three, is refused, not approved: absence of proof is treated as absence of approval.

This went through three same-day hardening stages, the second and third each closing a real, independently-reproduced bypass of the stage before it — not a hypothetical one:

- **Check 3 alone** (the original, un-numbered version) trusted `/proc/<ppid>/cmdline` alone — caller-controlled data, independent of which binary is actually running. Two independent reviews reproduced a bypass: a plain compiled ELF (no `#!` line, so the kernel's argv-rewrite on shebang execution never applies) `execve()`'d itself with a fabricated `argv` reading exactly like a genuine broker invocation, forked a direct child running the real resolver, and was approved without ever touching the broker's code. **No filesystem write access to this checkout was needed or used.**
- **Check 1 added** in response: not caller-supplied, so the only way to satisfy checks 1+3 together is for a real Python interpreter process to hold `argv` equal to the broker's canonical path. This was still insufficient: two independent reviews reproduced a second bypass against checks 1+3 — a *genuinely real* `python3 <broker path>` process, honestly satisfying both, still runs `sitecustomize.py` (or `usercustomize.py`, where user-site is enabled) from any directory named in `PYTHONPATH`, during interpreter *startup*, before the target script's own top-level code executes. An attacker who controls the parent's environment plants that hook to fork the real resolver before the broker's body ever runs — again with **no filesystem write access to this checkout.**
- **Check 2 added** in response: requiring `-I` in the parent's own, execve-time-fixed argv is not spoofable by that same process's later behavior — a real interpreter cannot present `-I` in its own argv without isolated mode having genuinely been in effect for it from the very start, which forecloses the site-hook the second bypass relied on. Verified directly: the reproduced `sitecustomize` bypass fails to fire when `-I` is present, confirmed against this repo's own `notion_broker.py`, not just in the abstract.

**What this is.** A policy control against the failure mode that actually occurred — an agent (or a human at a shell) invoking the resolver directly — and against the two concretely-reproduced spoofing techniques above (argv/exe impersonation; environment-triggered interpreter startup-hook injection), which is a materially broader guarantee than the original single check provided.

**What this is not, and where hardening stopped.** A sandbox. A third independent review reproduced a bypass of check (b) *and* (c) together, unprivileged, with no filesystem write access and no elevated capability: `/proc/<ppid>/exe` is a kernel-tracked reference fixed at that process's own `execve()`, but `/proc/<ppid>/cmdline` is populated from that same process's own memory — ordinary, process-owned content it can rewrite at any time via a plain self-write to `/proc/self/mem`. A process that starts genuinely non-isolated (so its own `PYTHONPATH`-supplied `sitecustomize.py` hook fires once, for real) can, from inside that hook, overwrite its own argv memory to read `-I <canonical broker path>` before forking the resolver. Reproduced end to end against the unmodified function: the real resolver, forked from the rewritten process, was approved.

This is not a narrow gap a fourth check could close — it generalizes. `/proc/<ppid>/cmdline` is self-reported, process-owned memory, and any signal placed there is rewritable by that process before a child reads it, by construction. Check (a) (`/proc/<ppid>/exe`) is the only one of the three that is not process-owned memory content and does not fall to this technique; checks (b) and (c) both do. Hardening stops here rather than shipping a fourth argv-based check that a fourth review would disprove the same way. `LD_PRELOAD` (unaffected by `-I`, which implies `-E` — ignoring `PYTHON*` environment variables — but not libc-level ones) and a `.pth` file in a *global*, non-user site-packages directory (also unaffected by `-I`, which does not imply `-S`) are two further, independently confirmed routes to code execution before this function ever runs, at successively higher bars of required access.

The honest, final position: this is a real, working control against the failure mode that actually occurred — an agent or human shell-invoking the resolver directly is refused, unconditionally, with no known bypass. It is **not** a barrier against a co-resident process capable of running arbitrary code, which can reach this resolver as a descendant without ever needing filesystem write access to this checkout. The residual boundary claimed precisely: write access to this checkout, control of a mount/overlay at the resolved canonical path, or the ability to run arbitrary code as a process that can reach this resolver as a descendant — full stop, regardless of what further checks are added to this function. Such an attacker could also simply edit `credential_registry.json` directly and remove the restriction entirely; that level of access is already the trust boundary every other control in this document assumes (see §2.2, "Privilege reality"). Do not repeat "agents can no longer raw-access this credential" without this qualification attached.

**Scope, stated precisely because it's easy to conflate:** this gates the raw credential *value*, not Notion *capability*. `scripts/notion_broker.py` is a plain script with no caller-identity check of its own — any process able to run code as this user could always invoke it directly and use its allowlisted, secret-scanned Notion capability, with or without ever touching `_caller_is_approved`. The argv-rewrite bypass documented above lets an attacker reach the resolver *through* an impersonated caller, but it hands them nothing a direct broker invocation didn't already hand them: neither path exposes the raw value, and the property this section exists to guarantee — raw `NOTION_TOKEN` never reaching agent/chat/log/test output — holds in both cases. Closing the remaining gap for real means replacing "inspect an ambient parent from outside" with an authenticated channel the broker itself controls end to end (e.g. a Unix domain socket the broker owns, checked via `SO_PEERCRED`, which the kernel populates from the connecting process's real credentials at `connect()` time — not from that process's own readable/writable memory) — but that would answer a *different* question (should same-user code be restricted from invoking Notion capability at all, independent of credential exposure), which is a separate threat-model and ROI decision, not a gap in what this section already delivers. A real architecture change either way, out of scope for this incident-response fix, and not silently implied to already be solved here.

**The broker pattern.** For a restricted credential, exactly one script is named in `approved_consumers`, and that script resolves the value internally, performs the one governed operation it exists for, and returns only a sanitized result — never the raw value — to its own caller. `NOTION_TOKEN` → `scripts/notion_broker.py` is the first instance of this pattern; consumers elsewhere (e.g. `ryzalab-notion-mcp`) call the broker as a subprocess rather than resolving the credential themselves.

**When to use this vs. plain per-site/per-use approval (§7.2, `AGENTS_TAILSCALE_KEY`).** `agent_raw_access: false` is for a credential an agent must be able to *use* routinely through a fixed, narrow operation (a broker can be written for it). Per-use human approval remains the right control for credentials whose blast radius is too broad or too rarely-needed to justify building a broker (Infrastructure-vault entries, taxonomy rule 7).

---

## 5. Shared password policy

### 5.1 Current policy (N=2 customers)

`ryzalab_support` may share one password across customer sites at current scale. Per-site **LLT remains unique** even when the UI password is shared (LLTs are how scripted maintenance authenticates; rotating one customer's LLT must not affect others).

### 5.2 Mitigations that make this defensible

All four must be in place. If any one fails, the policy collapses and per-site unique passwords become mandatory.

1. **Vault discipline.** Proton Pass is SoT. No spreadsheet, no Notion, no email.
2. **Per-site LLTs.** Always unique. UI password sharing does not extend to API tokens.
3. **Tailscale ACL scoping.** Operator tag reaches only `tag:customer-ha` hosts on HA service ports (Appendix A).
4. **Rotation contract.** §6 below.

### 5.3 Tripwires — when shared password becomes mandatory-unique

Per-site unique `ryzalab_support` passwords become mandatory at the **first** of these events:

- Customer count reaches **N≥5** active sites.
- First customer with continuous camera coverage on minors or cognitively vulnerable adults.
- First customer signs a paid SLA (any tier).
- Any suspected compromise of the shared password (including loss of the operator's primary auth factor).
- HA backup of any customer site is exfiltrated, lost, or stored on uncontrolled media.

When any tripwire fires, the migration plan is: rotate password on every site, regenerate every per-site LLT, update vault, update each `secrets-[sitecode].env`. SLA: complete within 72 hours of tripwire detection.

---

## 6. Rotation contract

Rotate `ryzalab_support` password and **all** per-site LLTs on:

- **Offboarding** of a customer (site leaves RyzaLab management): rotate both for the offboarded site, and rotate the shared password across all remaining sites.
- **Suspected compromise:** any of the §5.3 tripwires.
- **Operator endpoint loss** (laptop stolen, primary auth factor lost).
- **Annual cadence** as backstop, regardless of incidents.

Rotation SLA: 72 hours from trigger detection. Rotation owner: the operator (Ryan Surencio). Rotation evidence: vault `last_rotated` field updated for every affected site, plus a Notion Work Log entry.

---

## 7. Operator continuity

Single-operator vaults have a single-point-of-failure for the customer: if Ryan is unavailable, no one can log into a customer's HA to fix something urgent.

### 7.1 Current state (acceptable at N=2)

No designated continuity contact. Customer's owner account remains the absolute fallback because the customer owns it.

### 7.2 Tripwire — required before this becomes load-bearing

Designate a Proton Pass emergency-access contact and document the contact's responsibilities **before**:

- First paid SLA customer goes live, **OR**
- Customer count reaches **N≥3**.

The contact does not need to be technical — they need to be able to release the vault to a designated technical responder under a defined trigger.

---

## 8. Customer disclosure

The credential recovery packet states (one line) that RyzaLab uses a dedicated maintenance account named `ryzalab_support`, distinct from the owner account, used only during agreed maintenance windows.

### 8.1 Tripwire — formal consent language

Before the **first non-referral customer** (i.e., not a friend or family member with implicit consent), add a single sentence to the RyzaLab service terms:

> "RyzaLab maintains a non-owner maintenance account on the customer's Home Assistant for agreed support and maintenance. The account is created during commissioning, scoped to this customer's site, and rotated on offboarding or suspected compromise. Credentials are stored in RyzaLab's encrypted vault and are not shared with third parties."

Until that customer signs, packet line is sufficient.

---

## 9. Business continuity & disaster recovery

The operator path is Tailscale → SSH → HA. When that path is unavailable, the customer must still be able to recover, even if the operator is unreachable for hours. RyzaLab's commitment is that **no single failure** — Tailscale outage, YAML damage, HAOS corruption, hardware death, or operator unavailability — leaves a customer without a recovery path. **Document each layer in the customer record and exercise the layers on a fixed cadence.** Untested recovery is decoration.

This section is the single answer to *"the appliance died, what do I do?"* — both for the operator and for a non-technical customer.

### 9.1 Recovery tiers

| Tier | Path | Initiated by | Used when |
|---|---|---|---|
| **P0 Prevention** | Git is SoT. Destructive YAML changes only via merged PR + `git pull` + `ha core check` + `ha core restart`. No agent (Claude / Codex / Cursor) writes directly to `/config` on a customer site. | Process | Always. P0 prevents most incidents that would require the recovery tiers below. |
| **P1 Config rollback (remote)** | `cd /config && git fetch origin && git reset --hard origin/main && ha core check && ha core restart`. | Operator (SSH) | YAML damaged but Tailscale and SSH intact. |
| **P2 Self-healing boot** *(Layer A)* | Boot-time hook auto-reverts `/config` to last-known-good Git SHA when `ha core check` fails on N consecutive boots. See §9.3. | Autonomous | Persistent post-deploy or post-reboot config invalidity, no human reachable. |
| **P3 Outbound emergency channel** *(Layer B)* | Cloudflare Tunnel (off by default; operator-activated via incident kill-switch). Independent of Tailscale control plane. See §9.4. | Operator (Cloudflare Access) | Tailscale control-plane outage or auth loss while customer Internet is up. |
| **P4 Tailscale recovery (customer-assisted)** | Customer opens HA UI on local network → Tailscale add-on → re-authenticate. Or operator approves device in Tailscale admin console after customer triggers re-auth on phone app. | Customer + operator | Tailscale auth/key expired. Internet otherwise healthy. P3 unavailable. See `tailscale-hardening.md`. |
| **P5 LAN operator** | Operator physically on customer LAN, uses `http://homeassistant.local:8123` or static IP. | Operator (on-site) | Tailscale unrecoverable remotely; operator on-site. |
| **P6 Customer rescue USB** *(Layer C)* | Pre-staged labeled USB at customer site. Customer plugs in + power-cycles; appliance auto-reinstalls HAOS, restores last verified backup, re-pulls config from GitHub. See §9.5. | Customer (with one-page recovery card) | Total appliance failure, HAOS damage, or any scenario where remote operator is unreachable. **No operator dispatch required to start recovery.** |
| **P7 Off-box backup restore (operator-driven)** | Operator restores from off-box backup using customer's owner credentials and a fresh HAOS install. Used when the customer can't run P6 themselves (e.g., they're traveling). | Operator (on-site or via P3) | P6 not feasible; operator can dispatch. |
| **P8 Hardware swap** | On-site swap of GMKtec; new unit boots from rescue USB → restores → joins Git → resumes. | Operator (on-site) | Hardware death; rescue USB is the bootstrap medium for the replacement unit too. |

The previous matrix had a single-point-of-failure between P1 and "operator dispatch": if Tailscale was down and no one was on-site, recovery was blocked. **Layers A / B / C close that gap.** Layer A removes most config-damage incidents from the human path entirely. Layer B gives the operator a parallel reach when Tailscale is the broken thing. Layer C makes the customer self-sufficient when neither A nor B applies.

### 9.2 The Joe's-Pi-died walkthrough

A worked example, in plain language, that the credential-recovery card mirrors. This is what the customer reads:

> Joe's smart home stops responding. He notices at 8pm. The cause turns out to be a failed SSD inside the appliance — total hardware death.
>
> 1. **Joe power-cycles the appliance** (existing break-glass step). No change. Display LED is off and stays off.
> 2. **Joe reads the recovery card** taped near the appliance: "If the appliance is dead, plug in the GREEN USB stick and power-cycle. Wait 30 minutes."
> 3. **Joe plugs in the green USB** that RyzaLab handed over at install. He power-cycles. The appliance boots from USB and runs an automated restore: HAOS reinstalls onto the SSD, the latest verified backup applies, the appliance pulls latest config from GitHub, services start. (Still hardware-dead in this case, because the SSD itself failed — so the restore halts at "destination drive unreadable.")
> 4. **The recovery card's step 4** says: "If the green light on the USB stays red after 30 minutes, the appliance hardware is the problem. Call us at [number]. We will overnight a replacement unit." RyzaLab dispatches a replacement GMKtec, pre-imaged from the rescue USB workflow.
> 5. **Joe plugs in the replacement** when it arrives. The replacement boots from USB → installs HAOS → restores latest backup → pulls latest config → comes online with all his automations and devices intact. Joe's involvement is "plug it in and power it on."
>
> Total customer-facing complexity: read three numbered steps on a card. Total downtime: hours, not days. RyzaLab is reachable but not on the critical path until step 4.

When Tailscale and config are broken (no hardware death), the same card directs Joe to step 1 only; Layer A self-heal handles the rest autonomously, usually before Joe notices.

### 9.3 Layer A — Self-healing GitOps boot

**Pattern:** Immutable infrastructure / Kubernetes-operator-style "desired state from Git on every boot." Industry analog: NixOS, ChromeOS A/B partitioning, Kubernetes controllers.

**Behavior:**

1. On every HA boot, a recovery hook reads `/config/.last_green_sha` (the most recent SHA whose post-deploy verification passed).
2. If `git rev-parse HEAD` ≠ `$LAST_GREEN_SHA`, the hook runs `git fetch origin && git reset --hard $LAST_GREEN_SHA && ha core restart`.
3. If `ha core check` fails on three consecutive boots, the hook reverts further (one tag back, then two, until a green tag is found) and writes an incident record to `/config/.recovery/incidents.jsonl`.
4. `.last_green_sha` is written by post-deploy verification: deploy → wait 5 minutes → if `ha core check` + `tailscale status` + dashboard fetch all pass, write current SHA + tag as `last-green-[ISO date]` and push the tag.
5. Auto-revert frequency is monitored: more than two auto-reverts in 14 days for a single site triggers a P0 backlog item — the discipline is failing somewhere upstream.

**What this does not do:** does not silently mask failures forever. The incident counter and `.recovery/incidents.jsonl` are observable; an auto-revert that recurs is escalated to humans.

**Implementation owner:** Ryan. **Tracked in:** `docs/tasks/Tasks-Business-Continuity.md` BC-1.

### 9.4 Layer B — Outbound emergency channel

**Pattern:** Outbound-only HTTPS from edge device to a cloud-hosted relay; operator authenticates at the relay's identity layer to reach the device. Industry analogs: AWS Systems Manager Session Manager, Cloudflare Tunnel + Cloudflare Access, Azure Arc, Google Cloud IAP TCP forwarding.

**Choice:** **Cloudflare Tunnel + Cloudflare Access.**

- **Why CF Tunnel:** free at this scale, outbound-only (no port forwarding, no inbound on customer's NAT), authenticated at CF's identity layer (Zero Trust / Access policies), audited (every session logged), and revocable in seconds.
- **Why not Nabu Casa Cloud:** vendor lock-in to HA-only access (doesn't help with SSH-level recovery), $6.50/mo per site, and the trust model is the same kind of "outbound to vendor cloud" so it doesn't add a *different* failure mode from CF.
- **Why not self-hosted reverse SSH bastion:** RyzaLab would now operate infrastructure that becomes a single point of failure for *every* customer if the bastion VPS dies. CF Tunnel offloads the relay to a hyperscaler.

**Operational rules:**

1. **Off by default.** The `cloudflared` service on each customer appliance is installed and configured but **disabled** in steady-state. The tunnel only runs when the operator activates it during an incident.
2. **Per-site config.** Each site has its own CF Tunnel UUID, its own Access policy (only `ops-operator@ryzalab` can reach it), and its own audit log.
3. **Customer consent.** Per §8 disclosure, the customer is informed at install that an emergency-only Cloudflare path exists and is dormant unless RyzaLab activates it for an incident. If the customer declines, the site is documented as "no Layer B" and the rescue USB (Layer C) becomes the primary backstop for Tailscale-down scenarios.
4. **Activation procedure** (operator runbook, not policy):
   - Operator triggers a CF Access-authenticated webhook (or a customer pushing a labeled button on a printed card) → cloudflared starts on the appliance → operator reaches HA UI / SSH via `https://[sitecode].emergency.ryzalab.com` (placeholder; final hostname per Tunnel config).
   - Session expires after 4 hours; tunnel is stopped automatically.
5. **Token rotation.** CF Tunnel credentials and Access policies rotate on the same triggers as §6.

**What this does not do:** does not replace Tailscale. Tailscale remains the steady-state path for performance, latency, and lower trust-party count. CF Tunnel exists *only* as the parallel reach during a Tailscale incident, with a different blast radius and different control plane.

**Implementation owner:** Ryan. **Tracked in:** `docs/tasks/Tasks-Business-Continuity.md` BC-2.

### 9.5 Layer C — Customer rescue USB + recovery card

**Pattern:** Pre-staged recovery medium at the customer site, designed for non-technical operation. Industry analogs: Synology DSM recovery USB, Apple Time Machine boot, ATM field-service kit, Tesla service mode USB.

**Hardware:** USB 3 stick, ≥32GB, in a labeled green enclosure stored with the credential recovery packet. Cost: ~$15–20 per site.

**Contents:**

1. UEFI-bootable HAOS installer (latest stable at refresh time).
2. Most-recent-verified `.tar` HA backup for that site.
3. Auto-restore script that on first boot from USB:
   - Installs HAOS to internal SSD,
   - Restores the bundled `.tar`,
   - Pulls latest config from `github.com/surencio/ryzalab-[sitecode]-main` using a per-site read-only deploy key,
   - Re-authenticates Tailscale from a pre-issued reusable auth key (90-day TTL, refreshed on each USB refresh),
   - Reports completion via a status LED on the GMKtec or a printed completion message on a connected display.
4. Per-site identifier on the USB label so a USB cannot be used at the wrong site.

**Treat as credential-grade.** The USB carries a backup that contains hashed HA passwords + a deploy key + a Tailscale auth key. Stored in the same sealed envelope as the credential recovery packet (or a parallel sealed bag), with the same physical-security expectations (do not photograph, do not email). Treat USB loss as a §5.3 tripwire — rotate the deploy key, the Tailscale auth key, and `ryzalab_support`.

**Customer-facing recovery card** (one printed page, taped near the appliance, mirrored in the credential recovery packet §11):

```
┌─────────────────────────────────────────────────────────────┐
│  RYZALAB SMART HOME — EMERGENCY RECOVERY                    │
│                                                             │
│  If your smart home is unresponsive:                        │
│                                                             │
│  1. Unplug the white box. Wait 30 seconds. Plug it back in. │
│     Wait 5 minutes. Try again.                              │
│                                                             │
│  2. Still broken? Plug in the GREEN USB stick (labeled      │
│     RYZALAB RESCUE — [SITECODE]). Power-cycle the white     │
│     box. Wait 30 minutes. Do not unplug the USB.            │
│                                                             │
│  3. Still broken? Call RyzaLab: [phone].                    │
│                                                             │
│  Lights, locks, and thermostats still work manually while   │
│  the smart home recovers. You are not locked out.           │
└─────────────────────────────────────────────────────────────┘
```

**Refresh cadence:**

- Backup contents refreshed at the **90-day customer health check** (per `CUSTOMER_IMPLEMENTATION_PLAYBOOK.md` §4.3).
- HAOS installer image refreshed on the USB **annually** or when a HAOS major version changes the boot or recovery procedure.
- Tailscale reusable auth key on the USB rotated **quarterly**.

**Implementation owner:** Ryan. **Tracked in:** `docs/tasks/Tasks-Business-Continuity.md` BC-3.

### 9.6 Layer D — Disaster recovery drill cadence

Untested recovery is decoration. Drills are mandatory and observable.

| Cadence | Drill | Pass criterion | Owner |
|---|---|---|---|
| **Monthly** | Off-box backup restore-to-bench (existing §9.8). Rotate which customer site is tested. | Bench HAOS boots, owner login works, dashboard loads with no broken cards. | Ryan |
| **Quarterly** | Full Layer C drill on bench appliance: simulate "operator unreachable, customer has only the rescue USB and recovery card." Operator (in customer role) follows the card with no other tools. | Recovery completes within RTO target (current target: 2 hours). RTO actually achieved is logged. | Ryan |
| **Quarterly** | Layer A self-heal regression test: introduce an intentionally-broken commit on a bench site, reboot, confirm auto-revert fires and `.recovery/incidents.jsonl` records the event. | Auto-revert restores last green SHA; counter increments. | Ryan |
| **Quarterly** | Layer B activation drill: activate CF Tunnel on bench appliance with Tailscale forcibly disabled; verify operator reach via CF Access; verify auto-stop after 4 hours. | Tunnel comes up, auth holds, audit log captures session, tunnel auto-stops. | Ryan |
| **Annually** | Customer-facing tabletop walkthrough during the 90-day or annual visit. Walk the customer through reading the recovery card and identifying the green USB. | Customer can locate USB, identify the card, and read steps 1–3 without operator prompting. | Ryan |

**Drill artifacts.** Each drill writes an entry to Notion Work Log with `dr-drill` tag including: drill type, RTO achieved vs target, deviations, follow-up actions. Failed drills are P0 — the recovery layer is broken in policy until the failure is addressed.

**Tripwires for elevating cadence:**

- After any real-world Layer A/B/C activation: rerun the corresponding drill within 7 days.
- After any HAOS major version: rerun monthly + quarterly drills within 14 days.
- After any Tailscale or Cloudflare account ownership change: rerun Layer B drill within 7 days.

**Implementation owner:** Ryan. **Tracked in:** `docs/tasks/Tasks-Business-Continuity.md` BC-4.

### 9.7 RTO / RPO targets

For business continuity to be measurable, the recovery layers map to explicit RTO (Recovery Time Objective) and RPO (Recovery Point Objective) targets:

| Failure class | Layer that handles it | RTO target | RPO target |
|---|---|---|---|
| YAML/config damage, customer Internet up, Tailscale up | P1 (operator git reset) | 5 minutes | 0 (Git is canonical) |
| YAML/config damage, persistent across reboots | P2 / Layer A (auto-revert) | 15 minutes (autonomous) | 0 |
| Tailscale auth/control plane lost, customer Internet up | P3 / Layer B (CF Tunnel) | 30 minutes | 0 |
| Customer Internet up, customer can re-auth | P4 (Tailscale customer-assisted) | 1 hour | 0 |
| Total appliance failure or HAOS damage, customer present | P6 / Layer C (rescue USB) | 2 hours | ≤ 24 hours (last off-box backup) |
| Hardware death, replacement required | P8 (swap + USB bootstrap) | 24 hours from detection | ≤ 24 hours |

These are targets, not promises, until the drills validate them. Each quarterly drill records actual RTO; targets above are revised when measured RTO consistently differs by more than 30%.

### 9.8 Off-box backup verification cadence

Off-box backups are the load-bearing artifact for P6, P7, P8 and Layer C. Untested backups are decoration. Standard:

- **Monthly:** restore the most recent off-box backup of one customer site to a bench HAOS instance. Verify boot, owner login, dashboard load.
- Rotate which customer site is tested each month so every site is exercised at least quarterly.
- **Two off-box copies, distinct providers.** One in a RyzaLab-controlled object store (e.g., Backblaze B2 or AWS S3 with object lock), one in a separate location (NAS at operator residence, encrypted external drive in a fireproof safe, or vault provider's encrypted attachment). Same backup file, two physically and administratively independent stores. Loss of one provider does not lose the backup.
- Log every monthly verification in Notion Work Log with `backup-verify` tag, including SHA-256 of the verified `.tar`.
- Failed restore is a P0 incident — open a Backlog item immediately and rotate to next customer's backup as a sanity check.

This cadence is mandatory at N≥1 paid customer. Skipping a month requires written justification in the Work Log.

---

## 10. Observability scope (what we explicitly are not building yet)

Access management does **not** depend on a central log / metrics database. At current scale (N=2), incident-only excerpts captured to Notion (Work Log + incident template) is sufficient.

### 10.1 What we collect today

- Incident-only HA log excerpts pasted into a Notion incident entry.
- Operator session notes in Work Log (per `CLAUDE.md` SSRP rules).
- HA's own recorder data on each customer appliance (local, customer-owned, not exfiltrated).

### 10.2 What we do not collect

- No automated log shipping off-box.
- No central PostgreSQL / TimescaleDB / log-native store across customers.
- No cross-customer dashboards or telemetry aggregation.

### 10.3 Tripwires — when central observability re-enters scope

Canonical PRDs for a future central observability platform are scheduled to land in this repo at `docs/prd/PRD-HealthOps.md` and `docs/prd/PRD-HA-TELEMETRY-PLANE.md` in the `v0.2.0` migration wave (see `MIGRATION_PLAN.md` Phase 4). At `v0.1.0` (current platform release for this standard), `docs/prd/` is an empty placeholder — the PRDs still live in `surencio/ryzalab-austin-main` `main` until they migrate. Once present in platform, customer repos consume them via the pinned-version `docs/UPSTREAM/` mirror like every other governance doc.

**Until `docs/prd/` is populated:** the live canonical PRDs are at `surencio/ryzalab-austin-main` on `main`, paths `docs/prd/PRD-HealthOps.md` and `docs/prd/PRD-HA-TELEMETRY-PLANE.md` (filenames verified via `gh api repos/surencio/ryzalab-austin-main/contents/docs/prd`). Browse (logged in): `https://github.com/surencio/ryzalab-austin-main/tree/main/docs/prd`. Anonymous `https://raw.githubusercontent.com/...` returns **404** for private repos — use `gh api` or the web UI.

**Build** the central observability platform when the **first** of these is true:

- Customer count reaches **N≥5** active sites.
- First paid SLA contract requires proactive monitoring or a defined response time on system-down.
- First cross-customer incident requires correlated search ("did this same issue hit other sites?").
- A regulatory or insurance requirement specifies retention or audit logging.

Until then, this document explicitly defers it. Do not let "we should probably have logs" become an unscoped infrastructure project.

---

## 11. Gate-2 commissioning checklist

Adds the following rows to `CUSTOMER_IMPLEMENTATION_PLAYBOOK.md` Gate 2 (and is mirrored in §2.7 of the playbook):

**Access management:**

- [ ] `ryzalab_support` HA user created (admin) on customer appliance
- [ ] Per-site LLT generated for `ryzalab_support` and stored in Proton Pass
- [ ] `secrets-[sitecode].env` on operator laptop matches vault
- [ ] Tailscale machine name = `ha-[sitecode]` (verified in Tailscale admin console)
- [ ] Tailscale ACL covers this site (Appendix A)
- [ ] One end-to-end maintenance smoke test executed: WSL → SSH → `ha core check` → ha-mcp `ha_search_entities` (or equivalent)
- [ ] Vault entry `created` / `last_rotated` timestamps populated

**Business continuity (§9):**

- [ ] **Layer A — self-heal:** `/config/.last_green_sha` initialized to the deploy SHA after first successful post-deploy verification; recovery hook installed and tested with one intentional rollback on bench
- [ ] **Layer B — outbound channel:** Cloudflare Tunnel configured per-site, **disabled** in steady state, Access policy created scoped to operator identity, customer informed (or refusal documented if declined)
- [ ] **Layer C — rescue USB:** physical USB prepared, labeled `RYZALAB RESCUE — [SITECODE]`, contents include verified HAOS image + most recent verified backup + per-site deploy key + per-site Tailscale auth key; restore tested on bench appliance from this exact USB
- [ ] **Recovery card** (§9.5) printed and placed near the customer's appliance, plus a copy in the credential recovery packet
- [ ] **Two off-box backup copies** in distinct provider locations (§9.8); both verified
- [ ] First DR drill scheduled in Notion Backlog within 90 days of handoff

A site is not "remotely manageable" until every access-management row passes. A site is not "**operationally complete**" — i.e., handoff-ready — until every business-continuity row also passes.

---

## 12. Out of scope (defer triggers in §5.3 / §7.2 / §8.1 / §10.3)

- Multi-tenant access portal. Defer until customer count reaches **N≥10** OR first SLA customer requests self-service.
- Automated provisioning of `ryzalab_support` per site (currently manual during bench build). Defer until **N≥5**.
- ACL-as-code in this repo with CI validation. Defer until **N≥5** OR Tailscale ACL changes more than monthly.
- Central observability (see §10.3 triggers).
- **Out-of-band cellular failover** (LTE/5G modem on customer appliance for recovery when customer's home Internet is *also* down). Cost ~$240–480/yr/site; over-engineered at current scale because Layers A + C handle most non-Internet-dependent failures and most home-Internet outages resolve within hours. Defer until first SLA contract specifying recovery-during-ISP-outage, OR a customer with health-critical automations (medical alerts) requires uptime independent of customer ISP.
- **Encrypted-backup-from-cloud rescue variant** (USB carries no backup, fetches encrypted backup from RyzaLab object store using a customer-derived recovery code on first boot). Lower physical-theft blast radius but higher implementation complexity. Defer until **first non-referral customer** OR **first customer who declines storing a credential-grade USB on premises**.

---

## Appendix A — Tailscale ACL stanza

This is the canonical ACL pattern. Update the live `acl.hujson` in the Tailscale admin console to match whenever a new customer site joins the tailnet.

```hujson
{
  // Operator tag — the human (Ryan + future operators) when on RyzaLab business.
  "tagOwners": {
    "tag:ops-operator": ["autogroup:admin"],
    "tag:customer-ha":  ["autogroup:admin"],
  },

  "acls": [
    // Operator → customer HA hosts only, on HA service ports only.
    {
      "action": "accept",
      "src": ["tag:ops-operator"],
      "dst": [
        // HAOS does not expose port 22 by default; the operator path is the
        // Advanced SSH add-on on 2222. Add :22 only on sites where a host-OS
        // SSH is intentionally exposed (non-default — document the exception).
        "tag:customer-ha:2222",   // HA Advanced SSH add-on
        "tag:customer-ha:8123",   // HA Web UI
      ],
    },
    // Customer-owned devices reach their own HA on the local tailnet.
    // (Customer-side ACLs out of scope of this stanza.)
  ],

  "ssh": [
    // Tailscale SSH for operator → customer HA host as root, with re-check.
    {
      "action":      "check",
      "src":         ["tag:ops-operator"],
      "dst":         ["tag:customer-ha"],
      "users":       ["root"],
      "checkPeriod": "12h",
    },
  ],
}
```

When provisioning a new customer site:

1. Tag the customer HA host with `tag:customer-ha` in the Tailscale admin console.
2. Verify operator laptop has `tag:ops-operator`.
3. Confirm SSH and Web UI reachable from operator laptop only — not from other tagged devices that should not reach the customer.

---

## Appendix B — `secrets-[sitecode].env` template

```bash
# ~/.config/ryzalab/secrets-par.env
# DO NOT COMMIT. Mirror of the Proton Pass entry for site = par.
# Last synced: 2026-04-26

export RYZALAB_SITE=par
export HA_BASE_URL="https://ha-par.[tailnet].ts.net:8123"
export HA_TAILSCALE_IP="100.x.y.z"
export HA_TOKEN="[per-site LLT for ryzalab_support]"
export SSH_HOST="ha-par"
```

Source for one site at a time:

```bash
source ~/.config/ryzalab/secrets-par.env
# now HA_BASE_URL / HA_TOKEN are set for site = par only
```

If you find yourself sourcing two sites in the same shell, open a new terminal. Wrong-customer command execution is a P0 incident.

---

## Revision history

| Date       | Version | Change |
|------------|---------|--------|
| 2026-04-26 | 1.0     | Initial standard. Replaces "operator service account" language across runbooks. Establishes Proton Pass SoT, `ryzalab_support` canonical name, ha-[sitecode] Tailscale naming, P0–P5 rollback ladder, shared-password tripwires, monthly backup verification cadence. |
| 2026-04-26 | 1.1     | Closed the "Tailscale down + customer non-technical" single-point-of-failure gap. §9 rewritten as full business-continuity / DR section with four added recovery layers: Layer A self-healing GitOps boot (auto-revert to last green SHA), Layer B outbound emergency channel (Cloudflare Tunnel + Access, off by default), Layer C customer rescue USB + one-page recovery card, Layer D quarterly DR drill cadence. Added §9.2 Joe's-Pi-died worked example, §9.7 RTO/RPO target table, two-off-box-copy requirement in §9.8. Gate-2 (§11) extended with BC commissioning rows. Out-of-scope (§12) extended with cellular failover and cloud-fetched-backup variant triggers. Cursor non-blocking findings addressed: §10.3 PRD references corrected (golden-master cross-repo); Appendix A port 22 dropped (HAOS doesn't expose). |
| 2026-04-27 | 1.2     | §10.3: golden-master PRD paths verified on `main` (`gh api …/contents/docs/prd`); documented private-repo access (no raw.githubusercontent.com); org slug `surencio/ryzalab-austin-main`. |
| 2026-04-29 | 1.3     | Migrated from `surencio/ryzalab-par-main/docs/runbooks/` to `surencio/ryzalab-platform/docs/standards/` as Phase 2 of platform-as-SSOT migration (see platform's `MIGRATION_PLAN.md`). New §4.5 added for **operator-cross-site credentials** (NOTION_TOKEN, GITHUB_TOKEN, CLOUDFLARE_API_TOKEN) — distinct sourcing file `secrets-operator.env` from per-site files; closes the gap observed 2026-04-28 where NOTION_TOKEN was duplicated across per-site files with a stale 401-invalid copy. §10.3 rewritten: PRD references now scheduled to land in platform's own `docs/prd/` at `v0.2.0`; until then live canonical remains austin-main with private-repo access guidance. New BC-7 backlog row tracks the secrets-rehome migration in `docs/tasks/Tasks-Business-Continuity.md`. |
| 2026-08-19 | 1.4     | New §4.6 added for **agent raw-value access** (`agent_raw_access` / `approved_consumers` on `credential_registry.json` entries, enforced by `ryzalab_secret.py:_caller_is_approved`) after an incident where an agent printed a live `NOTION_TOKEN` value into a transcript via `get NOTION_TOKEN \| head`. Documents the gate and the broker pattern (`NOTION_TOKEN` → `scripts/notion_broker.py`, the first instance). Written to close a broken `§4.6` citation that shipped in `ryzalab_secret.py` and `credential_registry.json` pointing at a section that did not yet exist. Same-day revision history for this one section, four rounds, three independent reviews, each reproducing a real bypass of the round before it: (1) first version documented a single argv-path check and claimed bypass required checkout write access — false; reproduced via a compiled ELF faking its own argv. (2) Added a `/proc/<ppid>/exe` identity check — also insufficient; reproduced via a genuinely real interpreter running attacker code from a `PYTHONPATH`-supplied `sitecustomize.py` before its own body executed. (3) Added a required `-I` (isolated-mode) check that closes that specific mechanism — also insufficient; reproduced via an unprivileged, no-elevated-capability in-place rewrite of the parent's own argv memory (`/proc/self/mem`), which generalizes to defeat any signal placed in argv, not just `-I`. (4) This round: no further argv-based check attempted, since the finding proves that approach cannot be closed by adding more of the same; rewritten to state the final, evidenced boundary precisely — this control holds unconditionally against the incident's actual failure mode (direct shell/agent invocation) and against the two earlier concretely-reproduced spoofing techniques, and explicitly does not hold against a co-resident process capable of running arbitrary code, full stop; a real fix for that would replace ambient-parent inspection with an authenticated `SO_PEERCRED`-checked channel the broker itself owns, tracked as out-of-scope follow-up. |
