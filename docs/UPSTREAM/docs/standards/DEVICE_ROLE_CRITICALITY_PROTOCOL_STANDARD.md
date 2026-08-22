# Device Role-Criticality × Protocol-Weight Standard
**Version:** `v0.1.0` (Active)
**Date:** July 15, 2026
**Status:** Governed / Platform Standard — binding. Its protocol-ladder dependency
(`HA_BEST_PRACTICES_STANDARD.md §2.1`) merged 2026-07-15 (PR #89).
**Applies to:** device-selection and site-recommendation decisions — it sets how strongly the protocol
choice breaks a tie for a given device, and the `criticality_eligibility` floor its role requires, as a
function of what that device's **role** at the site demands. The **tier assignments** remain provisional
until calibrated per §9 — a normal new-standard state, not an unmet dependency.

> This standard is bound into the classification pipeline the same way the
> [Measurement Trust Overlay](IAQ_MEASUREMENT_TRUST_OVERLAY.md) is: it is a separate standard whose
> output participates in the site-recommendation decision. It **reuses** the existing
> `criticality_eligibility` vocabulary from `DEVICE_CLASSIFICATION_METHODOLOGY.md §9` and **references**
> the protocol ladder in `HA_BEST_PRACTICES_STANDARD.md §2.1`. It defines **no new device-class enum.**

---

## 1. Why this exists — the gap it closes

The Layer-2 rubric scores **deployment fit**. The measurement-trust overlay asks **is the number true**.
Neither asks the question a protocol standard raises: **how much does the protocol choice matter for
*this* device?**

`HA_BEST_PRACTICES_STANDARD.md §2.1` states a reliability-first protocol ladder — **Z-Wave > Zigbee >
Thread > Wi-Fi**. Applied as a flat universal preference it is wrong in both directions:

- It would **disqualify** the only devices that measure some signals well. Indoor-air-quality monitors,
  for example, are overwhelmingly Wi-Fi/Thread/BLE; a flat "Wi-Fi last" rule would reject the best
  measurement device to honor a ladder built for *switches*.
- It would **wave through** a cloud camera on the grounds that "cameras need Wi-Fi," conflating a
  bandwidth necessity with a sovereignty pass.

The ladder is fundamentally a **control-reliability** argument: avoid 2.4 GHz congestion, get wall
penetration, keep response times low, so a *family action* — flip a switch, lock a door — never fails.
**The strength of that argument is proportional to the cost of a single device failure.** A failed door
lock is a security event. A failed air-quality poll is one missing datapoint the next poll replaces.
Therefore the protocol choice must weigh **more for a lock than for a monitor**, and for one class it
**inverts**.

---

## 2. The role-criticality tier (R1–R5)

The tier is assigned by the **role the device plays at the site** — what it *controls or protects* —
**not by its device class.** A smart plug is a `switches_plugs` device class; a smart plug wired to a
**sump pump** is role-tier **R1**. Role is a site-overlay assignment (see §6), decided before scoring.

| Tier | Role (what a failure costs) | Examples | Protocol-tiebreak strength | Ladder (§2.1) applies |
|---|---|---|---|---|
| **R1** | **Life-safety / security** — a failure is a safety or security breach, irreversible or dangerous | door/garage locks, smoke/CO alarms, water shut-off, sump-pump control, leak valves | **DECISIVE** | Full strength. Prefer Z-Wave / sub-1 GHz; wired where possible. Local control **mandatory**; cloud in the daily path is disqualifying. |
| **R2** | **Comfort-critical** — a failure means an unhappy household or property risk (a dead thermostat in winter → frozen pipes) | thermostat/HVAC, primary lighting, primary door-access convenience | **STRONG** | Applies heavily. Local mandatory. R2 **escalates to R1** where a failure creates a safety/property hazard (freeze-risk, unattended property). |
| **R3** | **Convenience automation** — a failure is a mild annoyance with a manual fallback | scene/secondary lighting, blinds, non-primary plugs and switches | **MODERATE** | Applies moderately. Infrastructure-reuse tiebreak matters here. |
| **R4** | **Passive monitoring** — a failure is one missing datapoint that self-heals on the next reading | air-quality/CO2/PM, energy, environmental, non-safety sensors | **WEAK** | Applies weakly. Measurement-truth dominates. **Escalates** if the sensor *drives* an intervention (see §4). |
| **R5** | **Bandwidth-bound media** — a failure is a degraded stream; Z-Wave/Zigbee physically cannot carry the payload | cameras, doorbell video, speakers/voice | **INVERTED — split (see §5)** | The ladder **inverts** for *transport* (Wi-Fi/PoE is required for bandwidth). Sovereignty is scored **separately and does not invert.** |

**Protocol tier is NOT a Layer-2 score dimension.** The Layer-2 rubric's seven dimensions and weights are
fixed and CI-enforced in `scripts/device_classification_rules.py`; this standard does not add or reweight a
dimension (doing so would make the score non-computable and let two reviewers reach different classes). It
operates as **two deterministic, non-scoring controls** instead:

1. **A hard floor** (§6) — the role tier requires a minimum `criticality_eligibility`; a device below it is
   ineligible for the role. This is a gate, not points.
2. **A tiebreak** — among devices that pass gates *and* clear the floor, the role tier sets **how strongly the
   protocol ladder (§2.1) breaks a tie.** `DECISIVE` (R1): a protocol-superior device wins even over a
   higher-Layer-2-fit protocol-inferior one. `STRONG`/`MODERATE`: protocol breaks a near-tie within the
   §2.1-tiebreak's existing 10-point band (methodology §8). `WEAK` (R4): protocol breaks only a true tie;
   measurement-truth and sovereignty decide first. This removes the reweight-the-score gameability entirely —
   there is no protocol weight to pick.

---

## 3. Fleet-congestion term (the aggregate objection)

"A passive monitor failure is just a missing datapoint" is true for **one** device and false for **ten**.
Ten Wi-Fi sensors do not fail independently — they add airtime, retries, multicast, AP load, and
DHCP/mDNS noise to a **shared** 2.4 GHz medium, so their failures become **correlated** under congestion.
The per-device low-stakes reasoning ignores this fleet externality.

**Rule.** R4's `WEAK` tiebreak strength holds **per device up to a site 2.4 GHz budget**. Beyond it, each
additional 2.4 GHz-contending device (Wi-Fi, or Zigbee on a saturated mesh) **strengthens** the tiebreak for
new R4/R5 devices from `WEAK` to `MODERATE` (the R3 level) — i.e. sub-1 GHz / wired / Thread-border-routed
alternatives start winning ties. The site overlay must record **`rf_2g4_budget`** (the threshold),
**`rf_2g4_count`** (actual contending devices), and the survey **basis**. **Default `rf_2g4_budget`: 10**
(conservative single-AP starting point; raise only with a survey showing headroom). This makes the fleet
rule auditable — a number and a count, not a vibe.

> This makes "IAQ is R4, protocol barely matters" a **single-device** truth, not a licence to fill a
> room with Wi-Fi monitors.

---

## 4. Role escalation — R4 is not a free pass for sensors that act

A monitor that only *logs* is R4. A monitor whose reading *drives a must-work automation* — a CO2 sensor
triggering ventilation for a combustion appliance, a leak sensor closing a valve — has left R4. It is
governed by the automation it anchors: **R1 if the automation is safety-relevant, R2 if comfort-critical.**

This is consistent with, and enforced by, the existing rule in the measurement-trust overlay: an R4
device may only *anchor* a must-work automation if its `criticality_eligibility` is `PRIMARY_SAFE` — and a
`conditional`/`untrusted` measurement device is already capped below that. So a sensor that acts either
earns R1/R2 protocol rigor **or** is barred from anchoring the automation. There is no third path where a
cheap Wi-Fi sensor silently becomes load-bearing.

---

## 5. R5 media — transport inverts, sovereignty does not

R5 splits into two independent axes, scored separately:

- **Transport tier** — for a camera or speaker, high bandwidth is a hard requirement Z-Wave/Zigbee cannot
  meet, so Wi-Fi/PoE is *correct*, and the ladder's "Wi-Fi last" is **inverted** for transport only. PoE
  (wired) is preferred over Wi-Fi within R5.
- **Sovereignty tier** — a cloud-only camera is a sovereignty failure **regardless of bandwidth need.**
  The G1 local-control gate and the sovereignty tier registry (`CERTIFIED_STACK_v1.md §7`) apply to R5
  **unchanged**. Bandwidth necessity never buys a pass on local recording / no-vendor-cloud. **R5 floor:
  `T1` (Sovereign) required for the must-work recording path; `T2` (Cloud-assisted) only with a signed
  graceful-degradation exception; `T3` (Cloud-dependent) banned.**

A camera is only acceptable when it clears **both**: adequate transport (Wi-Fi/PoE) **and** local
recording with no cloud in the must-work path. Meeting one does not excuse the other.

---

## 6. How it binds (the composition)

The role tier is assigned in the **site-recommendation overlay** (a site decision, per role §2), and it
sets two things for that device's evaluation:

1. **A required `criticality_eligibility` floor (§6.1 table)** — the role's *demand* meets the device's *capability*.
   The role tier says what the site needs; `criticality_eligibility` (methodology §9, derived from
   gate + score + measurement-trust) says what the device can be trusted for. **The device must clear the
   floor:**

   **§6.1 — role floor table:**

   | Role tier | Requires `criticality_eligibility` ≥ |
   |---|---|
   | R1 | `PRIMARY_SAFE` |
   | R2 | `PRIMARY_SAFE` |
   | R3 | `SUPPORTED_NONCRITICAL` |
   | R4 (logging) | `SUPPORTED_NONCRITICAL` |
   | R4 (acting → see §4) | inherits R1/R2 floor |
   | R5 | `SUPPORTED_NONCRITICAL` transport **and** local-sovereign |

   A device whose capability is below its role's floor is **not eligible for that role** — pick a better
   device or downgrade the role's ambition. This reuses the §9 enum; it introduces no new vocabulary.

2. **The protocol tiebreak strength** applied among gate-passing, floor-clearing candidates (§2 table),
   subject to the fleet term (§3). This is a tiebreak, not a Layer-2 score change.

Role is a **site** property, not a device property (the same lock is R1 on a front door and R3 as a
gate-latch novelty), so it is stored in the **site overlay**, not the device record. The overlay carries a
dedicated block (`DEVICE_SITE_RECOMMENDATION_OVERLAY_TEMPLATE.md §1a`): **`role_tier`** (R1–R5),
**`controlled_function`** (what the device protects/controls, the assignment basis), **`required_criticality_floor`**
(from the §6.1 table), **`device_criticality_eligibility`** (the device's §9 capability), and **`floor_pass`**
(does capability ≥ floor). This reuses the §9 vocabulary for the *capability* value and adds **no** device-record
schema field — the new fields are site-overlay-only.

---

## 7. Protocol *security* tier (folded in from the retired certified-devices goal-loop)

Protocol *reliability* (the ladder) is not protocol *security*. The one non-duplicated idea worth keeping
from the archived `ryzalab-certified-devices` RCI prompt: **penalize obsolete link-security.** Within a
protocol, prefer the current security profile and down-score the legacy one:

- Z-Wave **S2** over S0 (S0 has known key-exchange weakness); **800-series** chips over 500-series.
- Zigbee **3.0** over 1.2; install-code pairing where available.
- Matter/Thread over Thread with current cert.

For an **R1** device this is a gate, not a preference: an R1 device on an obsolete security profile (e.g.
an old Schlage on S0) is capped at `SUPPORTED_NONCRITICAL` and cannot hold the R1 floor. For R3–R4 it is a
tiebreak. This replaces the phantom "protocol security tier" that the RCI goal-loop named but never
defined.

---

## 8. Anti-gaming — pre-registered, change-controlled weights

The protocol-tiebreak strengths in §2 and the fleet threshold in §3 are **fixed by this standard**, not free parameters an operator picks at decision time. The failure mode this guards against: choosing a role tier *after* seeing
which device you want, to justify it. Two controls:

1. **Role is assigned before scoring**, by function, in the site overlay, and is auditable against what the
   device actually controls.
2. **Changing a tiebreak strength or the RF-budget default is a change to this standard** — a versioned PR with cross-family review, not a
   per-site adjustment. Any site that deviates records an explicit exception with rationale, the same as a
   category-ceiling override.

> This standard was itself built after noticing the flat ladder disfavored certain Wi-Fi devices. That
> origin is exactly why the weights are frozen here and change-controlled: a knob you can turn to reach a
> preferred answer is not a standard. The weights must survive review on their own logic, not on which
> device they happen to select.

---

## 9. Provisional status & open calibration

`v0.1.0` is **active but not yet calibrated**. The floor logic (§6) and the gate+tiebreak mechanism
(§2) are binding now; the specific tier *assignments* are provisional until:

- The `rf_2g4_budget` default (§3) needs a real site-survey basis, not a guess.
- The role-tier assignments need calibration across 15–25 devices spanning all five tiers, at the same
  90%-agreement bar the methodology's §10 calibration uses.
- (resolved) The protocol ladder it references is live on main as `HA_BEST_PRACTICES_STANDARD.md §2.1`
  since 2026-07-15 (PR #89).

Reviewed via cross-family gate (codex `gpt-5.5/high` + qwen + composer pre-registered), 2026-07-15 —
which rated the underlying framework **SOUND-WITH-CHANGES** and required the fleet-congestion term (§3),
role-based assignment (§2, §6), the R5 sovereignty split (§5), and pre-registered weights (§8). All four
are incorporated. The review also corrected the accompanying device ranking from "highest analytical
score" to "**certification gates the choice**" — reflected in `CERTIFIED_STACK`, not here.

---

## Revision history

| Date | Version | Change |
|------|---------|--------|
| 2026-07-15 | 0.1.0 | Initial standard. Defines the role-criticality tier (R1 life-safety … R5 media) as a **site-assigned** axis that sets the required `criticality_eligibility` floor (reusing `DEVICE_CLASSIFICATION_METHODOLOGY.md §9`) and modulates the protocol-tier weight in the Layer-2 score (referencing `HA_BEST_PRACTICES_STANDARD.md §2.1`, pending PR #89). Incorporates the four cross-family-review-required fixes: fleet-2.4 GHz-congestion term (§3), role-based not device-class assignment (§2/§6), R5 transport-vs-sovereignty split (§5), and pre-registered change-controlled weights (§8). Folds in the protocol-security-tier idea (§7) salvaged from the archived `ryzalab-certified-devices` RCI goal-loop. Provisional: weights uncalibrated (§9). |
