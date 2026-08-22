# IAQ Measurement Trust Overlay
**Version:** `v0.1.0` (Active)
**Date:** July 12, 2026
**Status:** Governed / Platform Standard
**Applies to:** any device whose deliverable is a *number a human will act on* — air-quality
monitors, energy meters, water-flow sensors, leak/moisture probes.

---

## 1. Why this exists

The Verified Device Standard scores **deployment fit**: does it integrate, does it stay up,
does it work without the cloud, does it respect privacy. Nothing in it asks **is the number
true**. That is fine for a light switch, where "it turned on" is self-evidencing. It is not
fine for a monitor, where the entire product *is* the reading.

The gap is structural, not hypothetical:

- The `sensors` category has **no category ceiling** — so nothing caps a measurement device.
- The Layer 2 rubric has **no accuracy, calibration, or drift dimension**.
- Therefore a monitor that reports **confidently wrong numbers** can legitimately score
  `PREFERRED` / `PRIMARY_SAFE` and land on the Certified Stack. The AirGradient ONE scores
  90 and is correctly `PREFERRED` on fit — while shipping a CO2 calibration default that
  silently mis-zeroes in exactly the rooms customers most want measured.

**A false reading is worse than a missing one.** A dead sensor announces itself; a
confidently wrong sensor produces false reassurance and gets acted on.

## 2. Where it sits — and how it binds

```
Layer 1 hard gates (G1-G6)  →  MEASUREMENT TRUST OVERLAY  →  Layer 2 fit score  →  Site overlay
        eligibility               is the number true?           how well does it deploy
```

**This overlay is enforced, not advisory.** Every record carries a required
`measurement_trust` field, and it caps `device_class` through the same `min()` composition
as the hard gates:

| `measurement_trust` | Meaning | Caps `device_class` at |
| :--- | :--- | :--- |
| `not_applicable` | Device produces no metrological reading (switch, lock, occupancy) | — |
| `verified` | Channels trusted: independent eval or bench validation, defaults safe for the site | — |
| `conditional` | Usable, but a channel carries a known defaults or cross-sensitivity risk | `SUPPORTED_EXCEPTION` |
| `untrusted` | A decision-relevant channel cannot be trusted as deployed | `BEST_EFFORT_EXCEPTION` |

`SUPPORTED_EXCEPTION` maps to `SUPPORTED_NONCRITICAL` — **allowed in the home, never
anchoring a must-work flow.** That is the whole point: a monitor that can be confidently
wrong must not be able to reach `PRIMARY_SAFE` on the strength of a good integration.

CI rejects a record that describes a measurement device but declares `not_applicable` — you
cannot skip the overlay by leaving the field blank. Detection reads the primary capability
*and*, as a backstop against a euphemistic label like `environment_awareness`, the
metrological units (ppm, µg/m³, kWh, pCi/L, VOC Index) that G3 forces into the evidence.

**`conditional` is not the cheap way out.** It caps the device, so it looks like the safe
answer for a reviewer who does not want to do the work. CI therefore requires a
`conditional` or `untrusted` record to name the specific unresolved risk in `open_unknowns`
and carry a `review_by` date. A cap without a stated reason is not a review.

**Scope — the cap keys on the device's *primary* deliverable.** A wall switch that also
reports energy is still a switch: an imprecise power figure does not stop it switching, so
capping the device would demote a sound control product. Instead, the switch must list that
channel in `non_anchorable_channels` — **named as ineligible to anchor a must-work
automation**, so a `PRIMARY_SAFE` device cannot silently lend its criticality to an unvetted
number. A monitor, by contrast, **is** its reading: if the number is wrong, the product has
failed, and the whole device is capped.

**Honest limit.** All of this reads author-written fields. It is fail-closed and raises the
cost of skipping the overlay — the evidence backstop is hard to dodge without falsifying G3
evidence — but it cannot stop an author determined to lie in a record. The validator is a
speed bump; the reviewer is the wall.

## 3. The five checks

Deliberately five, not twelve. A twelve-row datasheet scorecard is the failure mode this
replaces: it is filled in from the vendor spec sheet, returns twelve green rows, and
catches none of the defects below — because **every real defect is an interaction between
the sensor and the room, not a property of the sensor.**

### C1 — Channel honesty flag *(per channel, mandatory)*

Label every exposed channel as exactly one of:

| Flag | Meaning | Example |
| :--- | :--- | :--- |
| `CONCENTRATION` | A calibrated physical quantity in real units | CO2 ppm (NDIR) |
| `INDEX` | A relative, self-baselining, unitless score | Sensirion VOC Index / NOx Index |
| `PROXY` | Measures something else and infers the thing you care about | CO2 as a ventilation proxy |
| `COUNT` | Particle counts, not mass — different units, different meaning | PM0.3 |
| `UNSPECIFIED` | Reported, but the vendor publishes no accuracy | AirGradient PM1 / PM10 |

**Never quote an `INDEX` channel as a concentration**, and never compare an `INDEX` value
across rooms or across time after a device move — it re-baselines to whatever room it is in.

### C2 — Evidence line *(per channel, mandatory)*

Vendor spec figure **plus** an independent evaluation — or the explicit token
`[NO PUBLIC EVAL]`. Do not imply a citation exists when it does not.

Reality check before you go looking: **for indoor monitors, public evaluation is a nearly
empty set.** EPA's sensor performance targets cover *outdoor ambient* sensors only. AQ-SPEC
evaluates outdoor units. An outdoor evaluation of a *different SKU from the same brand* is
not evidence about the indoor unit — that mistake is precisely how the wrong SKU (`O-1PST`)
ended up on the Certified Stack row for the ONE.

### C3 — Shipped-defaults vs. site *(mandatory — the check nothing else catches)*

**Does any factory-default self-correction assume something this room violates?**

This is the check that is invisible to honesty flags, to placement protocols, and to
co-location (two identical units drift the same way and agree with each other while both
are wrong). It is a *configuration* defect, and it is the highest-yield check in this
overlay.

The canonical case:

> **NDIR CO2 Automatic Baseline Calibration (ABC).** ABC tracks the lowest reading over its
> period and corrects it toward an assumed fresh-air 400 ppm, at roughly 30–50 ppm per
> period. It assumes the room returns to outdoor baseline periodically. **A
> poorly-ventilated basement never does** — so ABC drags the zero *downward* every cycle.
> Over a 6-week deployment on the AirGradient ONE's default 7-day period, that is on the
> order of 120–300 ppm of cumulative wrong correction, all of it in the direction of "this
> room is fine." The device manufactures a false improvement trend in the room you are
> trying to indict.
>
> **Mitigation:** disable ABC (exposed as a config entity in the HA integration), then
> manually calibrate in fresh air at the start of the deployment and again at the end. The
> start/end delta *is* your drift measurement and it costs nothing.

Ask the same question of every auto-correcting channel: MOx VOC self-baselining (~24 h
rolling window), auto-gain, auto-zero, adaptive filtering.

### C4 — Cross-sensitivity vs. site *(mandatory)*

**What does this room contain that this sensor is known to be fooled by?** Predictable from
datasheets; invisible to a generic scorecard. Known interactions:

| Sensor class | Fooled by | Failure direction |
| :--- | :--- | :--- |
| Optical PM (Plantower et al.) | High RH — particles absorb water and scatter more light; nonlinear above ~50% RH | **Over-reports** in damp rooms; no on-device RH correction |
| MOx VOC (SGP41 et al.) | **Siloxanes** — abundant in fabric softener, dryer sheets, detergents, personal care | **Irreversible sensitivity loss.** A MOx sensor in a laundry room degrades toward under-reporting |
| MOx VOC | Ethanol, cleaning sprays, solvents | Large excursions that mean "something changed," never "something is harmful" |
| NDIR CO2 | Being in an empty room (see C5) | Reads near-outdoor regardless of ventilation |

Note the pattern: **the common failure directions all point toward false reassurance.**

### C5 — Placement protocol + one co-location check *(mandatory)*

- **Placement:** distance from vents, purifiers, walls, windows, and occupants; and for
  moisture questions, whether a mid-air sensor can even see the failure mode (it usually
  cannot — see below).
- **Co-location:** run the new unit beside a second instrument, or beside itself before and
  after, for one overlapping period. Cheap, and it catches gross error.
- **Know what co-location cannot catch:** shared-mode error. Two units with the same ABC
  defect will agree with each other perfectly and both be wrong. Co-location validates
  *precision*, not *accuracy*. C3 is what catches accuracy.

## 4. Question–instrument fit (run this first)

The overlay above assumes the device can answer the question at all. Check that first,
because the most expensive error is not a mis-scored device — it is **buying a monitor that
structurally cannot answer the question asked.**

| The question | Can a consumer IAQ monitor answer it? |
| :--- | :--- |
| "Is there mould growing?" | **No.** Growth is governed by **surface** RH on cold walls (~80%+ sustained). Air at 20 °C / 60% RH has a dew point near 12 °C — any wall below that is condensing at 100% surface RH while a mid-room sensor reads a benign 60%. Correct instruments: **surface temperature vs. air dew point**, and a moisture meter. Air RH systematically under-detects this. |
| "Are there mould spores in the air?" | **No.** Spores are roughly 2–10 µm — mostly *above* the PM2.5 cut, and optical PM sensors count particles above ~1 µm poorly. An active mould problem can present as unremarkable PM2.5. |
| "Is this room adequately ventilated?" | **Only when occupied.** CO2 is a *metabolic tracer* — it rises because people exhale. An airtight, stagnant, empty room reads ~420 ppm and looks excellent. To get a real number, run a **CO2 decay test**: occupy the room, then measure the decay curve and compute air changes per hour. That is a legitimate quantitative measurement, but it must be *designed in*. |
| "What chemical is that?" | **No.** VOC/NOx are indices. They detect *change*, not identity, and not harm. |
| "Is my dryer venting into the room?" | **Check the duct.** A ten-minute visual inspection of whether the exhaust terminates outdoors dominates six weeks of PM2.5 logging. |

**Rule:** if the decisive instrument for the customer's actual question is a $20 IR
thermometer, a moisture meter, or a flashlight, say so. Selling a $230 monitor to infer
what a direct check would settle is a failure of advice, not a win.

## 5. Deployment obligations for adaptive-sensor devices

Any device carrying an `INDEX` channel or an auto-calibrating channel:

1. **Disable or pin auto-calibration** before the deployment starts; manually calibrate at
   start and end.
2. **Budget a warm-up.** NDIR ABC needs days to settle; MOx index needs ~24 h+ to learn a
   baseline. **Early data is invalid and must be discarded, not analysed.**
3. **Do not move the device mid-study** if you intend to compare rooms. Self-baselining
   channels re-normalise on arrival — a VOC Index of 100 downstairs and 100 upstairs are
   *not the same number*. Cross-room comparison needs two devices, or a fixed device and a
   different method.
4. **Configure retention.** Home Assistant's default `recorder` purge is **10 days**. A
   3-month evidence window with default retention arrives at the decision point with most
   of its evidence already deleted. Set `purge_keep_days` or long-term statistics on day 1.

## 6. Output

Two artifacts:

1. **`measurement_trust` in the classification record** — the machine-enforced verdict
   (§2). One value for the device, set by its weakest decision-relevant channel.
2. **A per-channel table appended to the site recommendation** — the reasoning behind it:

| Channel | Flag (C1) | Evidence (C2) | Defaults risk (C3) | Site cross-sensitivity (C4) | Trustworthy for this question? |
| :--- | :--- | :--- | :--- | :--- | :--- |

A channel that fails C3 or C4 for a given site is **not usable for that site's decision**,
even when the device's `device_class` is otherwise fine — site fit is narrower than
classification, never wider.

**Lifting a cap requires evidence, not argument.** Moving a device from `conditional` to
`verified` needs bench validation or an independent evaluation plus proof that the shipped
defaults are safe for the deployment — not a reviewer's confidence.
