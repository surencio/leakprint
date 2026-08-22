# Validation Rules
**Configuration & Naming Standards**

## Quick Reference

**Current enforced entity ID pattern (v1):** `[SITE]-[room]-[node]-[type]`

**Forward governance target (v2):** see [`docs/strategy/ENTITY_NAMING_V2_PROPOSAL_AND_RESEARCH.md`](strategy/ENTITY_NAMING_V2_PROPOSAL_AND_RESEARCH.md)
- Fixed infrastructure: `domain.<area>_<asset>_<function>`
- Movable assets: `domain.<asset>_<function>`
- System entities: `domain.sys_<function>_<metric>`

**SITE Prefix:** Configurable via `SITE_PREFIX` environment variable (default: `aus` for Austin)
- Austin deployment: `aus-lr-main-light`
- Houston deployment: `hou-lr-main-light`
- NYC deployment: `nyc1-lr-main-light`

**Common Room Codes:** `lr`, `kit`, `mbr`, `mbath`, `ofc`, `gar`, `hall`, `sys`

**Common Type Suffixes:** `-light`, `-switch`, `-sensmot`, `-sensbatt`, `-cam`

**Full details:** See Section 2 (Schema) and Section 3 (Taxonomy Tables)

## Transition Status

This document currently serves two jobs:

1. It remains the **current validator-enforced v1 schema** for the deployed estate and any entity IDs that must still pass the existing CI rules.
2. It provides the **room code and taxonomy source of truth** that v2 will continue to reuse for governed area slugs and compact display conventions.

The forward governance target is **Entity Naming Governance v2**, documented in [`docs/strategy/ENTITY_NAMING_V2_PROPOSAL_AND_RESEARCH.md`](strategy/ENTITY_NAMING_V2_PROPOSAL_AND_RESEARCH.md). Until the validator is updated, net-new IDs must still satisfy the current v1 enforcement rules.

---

> **Process Reference**: For the complete loop-based iterative workflow for renaming entities to platform naming compliance, see:
> - **Primary Process**: [`docs/REVIEW_ENTITIES.md`](REVIEW_ENTITIES.md) - Complete loop-based workflow with scoring model
> - **Product Requirements**: [`docs/ENTITY_NAMING_PRD.md`](ENTITY_NAMING_PRD.md) - Product requirements and acceptance criteria

## 1. Definition of Done
To consider a task "Done", it must meet these criteria:
1.  `hass-cli config check` passes.
2.  Gatekeeper workflow passes (pre-commit lint + `hass --script check_config` on `austin-pi`).
3.  Platform-governed asset IDs match the Schema (`aus-[room]-[node]-[type]`) and HA `entity_id` values are derived deterministically (see below).
4.  Added to README Inventory.

### 1.1 Entity Renaming Exit Criteria

When renaming entities to platform naming compliance, the process must meet **all** of the following exit criteria (per `docs/REVIEW_ENTITIES.md` Section 0):

1. **Unresolved queue size**: `<= 5` entities/devices are marked `MANUAL_REVIEW`
2. **Loop aggregate match score**:
   * `median(match_score) >= 0.90` **and**
   * `mean(match_score) >= 0.90`
3. **Loop aggregate confidence score**:
   * `median(confidence_score) >= 0.90` **and**
   * `mean(confidence_score) >= 0.90`
4. **Coverage constraint**:
   * At least **90% of in-scope rows** have `match_score >= 0.90` **and** `confidence_score >= 0.90`

"In-scope rows" means anything not marked `SKIP` or `DELETE`.

**Scoring Model**: See `docs/REVIEW_ENTITIES.md` Section 0 for complete match_score and confidence_score calculation formulas using string similarity functions (token-set ratio, Levenshtein, Jaro-Winkler).

### 1.2 Using Exit Criteria in Loop-Based Workflow

The exit criteria above are used at the **exit criteria checkpoint** (Gate R-Loop in `docs/ATOMIC_TASKS.md`) to determine whether to proceed with applying renames or loop back for refinement.

**Checkpoint Process:**

1. **Calculate Metrics:**
   ```bash
   python3 scripts/calculate_exit_criteria.py \
     --metrics artifacts/entity_review_metrics.csv \
     --out artifacts/exit_criteria_report.txt
   ```

2. **Review Report:**
   ```bash
   cat artifacts/exit_criteria_report.txt
   ```

   Expected output:
   ```
   Exit Criteria Assessment:
   =========================

   1. MANUAL_REVIEW count: 12 (target: <= 5) ❌
   2. median(match_score): 0.87 (target: >= 0.90) ❌
   3. mean(match_score): 0.84 (target: >= 0.90) ❌
   4. median(confidence_score): 0.91 (target: >= 0.90) ✅
   5. mean(confidence_score): 0.88 (target: >= 0.90) ❌
   6. Coverage (>= 0.90): 78% (target: >= 90%) ❌

   OVERALL STATUS: NOT MET (2/6 criteria passed)

   Recommended Action: REFINE AND LOOP BACK
   ```

3. **Decision:**
   - **If ALL criteria ✅**: Proceed to apply renames (Gate R5 in `docs/ATOMIC_TASKS.md`)
   - **If ANY criteria ❌**: Identify root cause, apply fix, loop back (Gate R1)

**Typical Loop Count**: 2-3 iterations to meet all criteria

**Practical Targets** (from historical execution):
- **PROPOSED rate**: >= 65-75% (achieved: 81.6% final)
- **CONFLICT rate**: <= 10% (achieved: 0% final)
- **Scores**: median/mean >= 0.90 for both match_score and confidence_score
- **Coverage**: >= 90% of entities with both scores >= 0.90

**Historical Performance** (from `docs/LESSONS_LEARNED.md`):
- **Loop 1**: Fixed implementation gap → 62.3% PROPOSED (was 2.1%)
- **Loop 2**: Fixed patterns and type inference
- **Loop 3**: Handled duplicate devices → 81.6% PROPOSED (final)

**Refinement Strategies**: See `docs/REVIEW_ENTITIES.md` Section 0 for detailed strategies when exit criteria are not met.

**Implementation Reference**: See `docs/ATOMIC_TASKS.md` Gate R-Loop for operational implementation of the exit criteria checkpoint.

## 2. Legacy v1 Naming Schema (current validator enforcement)

All entities must follow the strict 4-segment format.

**Format:** `[site]-[room]-[node]-[type]`

**Note:** The `[site]` prefix is configurable via the `SITE_PREFIX` environment variable (defaults to `aus` for Austin). See `docs/GITOPS.md` for configuration details.

### Segment rules (strict, automatable)
- **Hyphens (`-`) separate segments only**. Do **not** use hyphens inside any segment.
- **“Single-word” means single token**: segments must not contain spaces.
- **Allowed characters inside an Asset ID segment**: lowercase letters (`a-z`) and digits (`0-9`) only.
- **No underscores inside any Asset ID segment**: if you need multiple words, concatenate while preserving meaning (do not over-abbreviate).
  - Prefer `lampbulb1` over `bulb1` (UX + support clarity: retains parent context)
  - Prefer `islandmain` over `island` if there may be multiple island circuits
- **Node MUST NOT equal type**: avoid `light_light`, `switch_switch`. If node would equal type, use `group` as node.
  - Prefer `xmastree` over `xmas` if the node is specifically a tree plug

> **Note:** Do not use hyphens within a segment (e.g., `aus-kit-island-main-light` is INVALID). Do not use underscores in segments; concatenate instead (e.g., `islandmain`).

| Segment | Definition | Valid Examples (see Section 3 for complete taxonomy) |
| :--- | :--- | :--- |
| **Prefix** | Site identifier (configurable via `SITE_PREFIX` env var) | `aus` (default), `hou`, `nyc1`, etc. |
| **[room]** | Location code from [Location Taxonomy](#a-location-taxonomy-room) (Section 3.A) | `kit`, `lr`, `mbr` |
| **[node]** | Specific device descriptor (Function/Position) from [Common Node Descriptors](#b-common-node-descriptors-node) (Section 3.B) | `islandmain`, `overhead`, `desktask` |
| **[type]** | Controlled suffix vocabulary from [Domain Suffixes](#c-domain-suffixes-type) (Section 3.C) | `light`, `switch`, `sensmot` |

> **Note:** The examples above are illustrative. For the complete authoritative taxonomy of valid values for each segment, see [Section 3: Taxonomy Tables](#3-taxonomy-tables).

### Corrected Examples (Austin deployment, default)
* **Kitchen Island Light:** `aus-kit-islandmain-light` (Node concatenates tokens while preserving meaning)
* **Living Room Main:** `aus-lr-main-light`
* **Driveway Camera:** `aus-drv-front-cam`

**Note:** For other cities, replace `aus` with the configured `SITE_PREFIX` value (e.g., `hou-kit-islandmain-light` for Houston).

## 2.1 Legacy v1 user-facing layers (UI + voice)
The schema ID above is the **source of truth** for automation and inventory, but Home Assistant also has user-facing layers.

Example mapping (single entity):
- **Asset ID (docs/ops)**: `aus-lr-lampbulb1-light`
- **HA entity_id**: `light.aus_lr_lampbulb1_light`
- **Friendly name**: LR Lamp Bulb 1
- **Aliases**: Lamp bulb 1, LR lamp, Corner lamp bulb 1

### 2.2 Legacy v1 compact friendly-name convention

This section documents the compact room-code prefix convention used by the current deployed v1 estate and dense operational dashboards. The forward customer-facing naming policy for v2 lives in [`docs/strategy/ENTITY_NAMING_V2_PROPOSAL_AND_RESEARCH.md`](strategy/ENTITY_NAMING_V2_PROPOSAL_AND_RESEARCH.md) and [`docs/ENTITY_AUTOMATION_GOVERNANCE.md`](ENTITY_AUTOMATION_GOVERNANCE.md).

**Goal:** Friendly names must be short, consistent, and dashboard-readable.

**Rules:**
- Friendly names MUST use room abbreviations (e.g., `LR`, `MBR`, `MBATH`).
- Friendly names MUST NOT include brand names (Hue, Wiz, TP‑Link, etc.).
- Group entities MUST include `Group` in the friendly name.
- If `node == type`, replace node with `group` to avoid duplicates (e.g., `light_light` → `group_light`).

**Room Abbreviations (Required):**

| Room Code | Friendly Name Prefix |
| :--- | :--- |
| `lr` | `LR` |
| `kit` | `KIT` |
| `mbr` | `MBR` |
| `mbath` | `MBATH` |
| `bath2` | `BATH2` |
| `bath3` | `BATH3` |
| `guestbath` | `GBATH` |
| `guestbed` | `GBED` |
| `gar` | `GAR` |
| `ofc` | `OFC` |
| `hall` | `HALL` |
| `fpor` | `FPOR` |
| `bpor` | `BPOR` |
| `drv` | `DRV` |
| `ent` | `ENT` |
| `ext` | `EXT` |
| `nur` | `NUR` |
| `closprim` | `MCLOSET` |
| `lndry` | `LNDRY` |
| `sys` | `SYS` |
| `infra` | `INFRA` |

Example mapping (multi-entity device):
A single physical device (e.g., Aqara Motion Sensor 2 in stairway) can expose multiple entities, all sharing the same `[room]-[node]` base but with different `[type]` suffixes:
- **Asset IDs (docs/ops)**:
  - `aus-hall-stair-sensmot` (motion)
  - `aus-hall-stair-sensocc` (occupancy)
  - `aus-hall-stair-sensillum` (illuminance)
  - `aus-hall-stair-sensbatt` (battery)
- **HA entity_ids**:
  - `binary_sensor.aus_hall_stair_sensmot`
  - `binary_sensor.aus_hall_stair_sensocc`
  - `sensor.aus_hall_stair_sensillum`
  - `sensor.aus_hall_stair_sensbatt`
- All entities share the same `[room]-[node]` base (`aus-hall-stair`) but have different `[type]` suffixes

### Converting schema → Home Assistant `entity_id`
Home Assistant `entity_id` format is `domain.object_id`.
- **Domain** comes from the device class (e.g., `light`, `switch`, `binary_sensor`).
- **Object ID** should be a safe token; for platform naming mapping we use:
  - Replace hyphens (`-`) with underscores (`_`)
  - Keep tokens concatenated (Asset ID segments have no underscores by rule)

## 2.2 Multi-Entity Device Naming

Many Home Assistant devices expose multiple entities from a single physical device. For example, an Aqara motion sensor may expose motion, occupancy, illuminance, battery, and temperature entities.

**Key Principles:**
- One physical device can expose multiple entities
- All entities used in automations should receive platform-governed names
- Entities from the same device share the same `[room]-[node]` base but have different `[type]` suffixes
- Each functional entity gets its own Asset ID following the `aus-[room]-[node]-[type]` format

**Example: Aqara Motion Sensor 2 in Stairway**
- Device location: Hallway/Stairway
- Motion: `aus-hall-stair-sensmot` → `binary_sensor.aus_hall_stair_sensmot`
- Occupancy: `aus-hall-stair-sensocc` → `binary_sensor.aus_hall_stair_sensocc`
- Illuminance: `aus-hall-stair-sensillum` → `sensor.aus_hall_stair_sensillum`
- Battery: `aus-hall-stair-sensbatt` → `sensor.aus_hall_stair_sensbatt`
- Temperature: `aus-hall-stair-senstemp` → `sensor.aus_hall_stair_senstemp`

All entities share the base `aus-hall-stair` but use different type suffixes to distinguish their function.

## 2.3 Entity Naming Decision Framework

Not all entities from a multi-entity device need platform-governed names. Use this framework to decide which entities to rename.

> **Process Reference**: For the complete loop-based workflow that implements this decision framework with automated scoring and triage, see `docs/REVIEW_ENTITIES.md`.

### **Rename: Entities Used in Automations**

Entities commonly used in automations, dashboards, or voice commands should receive platform-governed names for discoverability and consistency:

- **Motion sensors**: `-sensmot` (binary_sensor)
- **Occupancy sensors**: `-sensocc` (binary_sensor)
- **Illuminance sensors**: `-sensillum` (sensor)
- **Battery sensors**: `-sensbatt` (sensor)
- **Temperature sensors**: `-senstemp` (sensor)
- **Humidity sensors**: `-humidity` (sensor)
- **Mode/state entities**: `-mode` (varies by domain)
- **Brightness controls**: `-brightness` (light)
- **Color controls**: `-color` (light)
- **Temperature controls**: `-temp` (climate/sensor)
- **Light controls**: `-light` (light)
- **Switch controls**: `-switch` (switch)
- **Lock controls**: `-lock` (lock)
- **Camera entities**: `-cam` (camera)
- **Input booleans**: `-inbool` (input_boolean)

**Decision rule**: If an entity is referenced in automations, dashboards, or voice commands, it should have a platform-governed name.

**Scoring for Rename Decisions**: When proposing renames, compute `match_score` and `confidence_score` per `docs/REVIEW_ENTITIES.md`:
- **Match Score**: Measures how well the proposed name matches the platform naming schema and evidence (room, node, type alignment)
- **Confidence Score**: Measures how safe it is to auto-apply without human review (considers YAML references, collisions, evidence strength)
- Entities with both scores `>= 0.90` can be automatically renamed
- Entities with scores `< 0.90` should be moved to `MANUAL_REVIEW` status

### **Skip: Diagnostic/Configuration-Only Entities**

Truly diagnostic or configuration-only entities that are not used in automations should be skipped:

- Firmware version entities
- Cloud connection status
- LED indicator controls
- Detection interval (settings)
- Motion sensitivity (settings)
- Any entity with `entity_category == 'diagnostic'` that is not used in automations

**Note**: Even if an entity has `entity_category == 'diagnostic'`, if it's used in automations (e.g., battery level for low-battery alerts), it should still receive a platform-governed name.

**System Entity Filtering**: System platform entities (hassio, sun, person, etc.) are automatically filtered out early in the rename process per `docs/REVIEW_ENTITIES.md`. These entities do not need platform-governed names.

## 2.4 Multi-Entity Device Examples

### Example 1: Aqara Motion Sensor 2 (Stairway)

**Device location**: Hallway/Stairway

**Entities to rename:**
- `aus-hall-stair-sensmot` → `binary_sensor.aus_hall_stair_sensmot` (motion)
- `aus-hall-stair-sensocc` → `binary_sensor.aus_hall_stair_sensocc` (occupancy)
- `aus-hall-stair-sensillum` → `sensor.aus_hall_stair_sensillum` (illuminance)
- `aus-hall-stair-sensbatt` → `sensor.aus_hall_stair_sensbatt` (battery)

**Entities to skip**: Firmware version, LED indicator, Detection interval (settings)

### Example 2: Hue Motion Sensor (Living Room)

**Device location**: Living Room

**Entities to rename:**
- `aus-lr-main-sensmot` → `binary_sensor.aus_lr_main_sensmot` (motion)
- `aus-lr-main-sensillum` → `sensor.aus_lr_main_sensillum` (illuminance)
- `aus-lr-main-senstemp` → `sensor.aus_lr_main_senstemp` (temperature)
- `aus-lr-main-sensbatt` → `sensor.aus_lr_main_sensbatt` (battery)
- `aus-lr-main-sensocc` → `binary_sensor.aus_lr_main_sensocc` (occupancy, if present)

**Entities to skip**: Firmware version, LED indicator, Configuration entities

### Example 3: Ecobee Thermostat (Living Room, via HomeKit)

**Device location**: Living Room

**Entities to rename:**
- `aus-lr-thermostat-temp` → `sensor.aus_lr_thermostat_temp` (temperature)
- `aus-lr-thermostat-humidity` → `sensor.aus_lr_thermostat_humidity` (humidity)
- `aus-lr-thermostat-mode` → `climate.aus_lr_thermostat_mode` (mode)
- `aus-lr-thermostat-sensmot` → `binary_sensor.aus_lr_thermostat_sensmot` (motion)
- `aus-lr-thermostat-sensocc` → `binary_sensor.aus_lr_thermostat_sensocc` (occupancy)

**Entities to skip**: Firmware version, HomeKit pairing status, Configuration entities

## 2.5 Validation and Scoring

### Schema Validation

An entity_id is **platform naming compliant** if it matches the pattern:
```
^[a-z_]+\.aus_[a-z0-9]+_[a-z0-9]+_[a-z0-9]+$
```

Examples:
- ✅ `light.aus_lr_lampbulb1_light` (compliant)
- ✅ `binary_sensor.aus_mbr_thermostatmot_sensmot` (compliant)
- ❌ `light.arcadia_masterbath_sl` (non-compliant - old pattern)
- ❌ `light.aus_mbath_sl` (non-compliant - missing node segment, should be `aus_mbath_[node]_light`)

### Scoring Model Reference

For automated rename proposals, the process uses a scoring model to validate proposed names:

- **Match Score**: Validates schema compliance, room/type/node alignment, and collision freedom
- **Confidence Score**: Validates operational safety (YAML references, evidence strength, dry-run status)

**Complete scoring formulas**: See `docs/REVIEW_ENTITIES.md` for:
- Match score calculation: `S_schema * S_collision * (0.30*S_room + 0.35*S_type + 0.35*S_node)`
- Confidence score calculation: `sigmoid(z)` with logistic transform
- String similarity functions: token-set ratio, normalized Levenshtein, Jaro-Winkler

**Exit Criteria**: The rename process continues in loops until all exit criteria are met (see Section 1.1 above).

## 2.6 Post-Rename Validation Checklist

After generating a rename plan, validate all PROPOSED entities using this checklist:

### Schema Validation
- [ ] All `new_entity_id` values match platform naming pattern: `^[a-z_]+\.aus_[a-z0-9]+_[a-z0-9]+_[a-z0-9]+$`
- [ ] All room codes are valid (see Section 3.A)
- [ ] All type suffixes are valid (see Section 3.C)
- [ ] No `node == type` patterns (e.g., `light_light`, `switch_switch`)

### Pattern Detection
- [ ] No duplicate `new_entity_id` values
- [ ] No collisions with existing entity IDs
- [ ] All sibling entities (same `device_id`) share same room code
- [ ] All sibling entities share same `[room]-[node]` base

### Consistency Checks
- [ ] Room code matches assigned area (if area assigned)
- [ ] Friendly names use room abbreviations (Section 2.2)
- [ ] Friendly names don't include brand names
- [ ] Group entities have "Group" suffix in friendly names
- [ ] Friendly names ≤ 35 characters

### Area Assignment
- [ ] All entities assigned to valid areas (if area assigned)
- [ ] Area names map correctly to room codes
- [ ] Sibling entities assigned to same area

**Reference**: See `docs/ENTITY_RENAME_QA_PRD.md` for complete QA loop specification.

## 3. Taxonomy Tables

### A. Location Taxonomy (`[room]`)

> **MANDATORY RULE**: ALL entities MUST have a room assignment. No entity may remain without a room code. If an entity's physical location is unclear, assign it to `sys` (HA infrastructure) or `infra` (network/technical infrastructure).

| Code | Area |
| :--- | :--- |
| `ext` | Exterior / Landscape |
| `fpor` | Front Porch |
| `bpor` | Back Porch |
| `ent` | Entryway |
| `lr` | Living Room |
| `kit` | Kitchen |
| `dr` | Dining Room |
| `hall` | Hallway |
| `mbath` | Master Bath |
| `bath2` | Bathroom 2 (Secondary Bath) |
| `bath3` | Bathroom 3 (Half Bath / Powder Room) |
| `mbr` | Master Bedroom (Main Bedroom) |
| `closprim` | Primary Closet (Master Closet) |
| `ofc` | Office |
| `gar` | Garage |
| `drv` | Driveway |
| `nur` | Nursery |
| `br1` | Bedroom 1 |
| `br2` | Bedroom 2 |
| `den` | Den / Family Room |
| `pat` | Patio |
| **`sys`** | **HA System/Infrastructure (backups, updates, sun, person, etc.)** |
| **`infra`** | **Technical Infrastructure (network, integrations, diagnostics)** |

#### Deprecated Room Codes

| Old Code | New Code | Notes |
| :--- | :--- | :--- |
| `bedprim` | `mbr` | Master Bedroom |
| `bathprim` | `mbath` | Master Bath |
| `system` | `sys` | System/Infrastructure |
| `porch` | `fpor` / `bpor` | Split into Front/Back Porch |
| `frontporch` | `fpor` | Front Porch |
| `gbr1` | `br1` | AIA-standard: Bedroom 1 |
| `gbr2` | `br2` | AIA-standard: Bedroom 2 |
| `gbath` | `bath2` | AIA-standard: reuse existing bath2 |
| `broom` | `den` | AIA-standard: Den / Family Room |

#### System Room Guidelines

The `sys` and `infra` room codes are for entities that don't have a physical location:

**Use `sys` for:**
- Backup entities (`event.backup_*`, `sensor.backup_*`)
- Home Assistant updates and version sensors
- Sun entities (sunrise, sunset, azimuth)
- Person entities
- Zone entities
- Automation/script metadata entities

**Use `infra` for:**
- Network diagnostic entities (RSSI, BSSID, Wi-Fi signal)
- Integration status entities
- Cloud connection entities
- Firmware/update entities for infrastructure devices

**Examples:**
- `aus-sys-backup1-event` → `event.aus_sys_backup1_event`
- `aus-sys-sun-sensazimuth` → `sensor.aus_sys_sun_sensazimuth`
- `aus-infra-wifidiag-sensrssi` → `sensor.aus_infra_wifidiag_sensrssi`

**Note on "Other" area:**
The **Other** area is a UI quarantine for unavailable/unknown entities. It is **not** a room code for naming. Use `sys`/`infra` for naming even if the entity is quarantined in the UI.

### B. Common Node Descriptors (`[node]`)
*These function as the "Function" or "Position" identifier. Use concatenation (no underscores) to keep segments single-token.*
| Suffix | Description |
| :--- | :--- |
| `main` | Primary overheads / main light group |
| `accent` | Strips, lamps |
| `task` | Desk/Work |
| `night` | Low-light |
| `fan` | Ceiling fan |
| `door` | Physical door |
| `front` | Front side of a shared room |
| `back` | Back side of a shared room |
| `islandmain` | Kitchen Island Main |
| `undercab` | Under-cabinet (e.g., WLED strips) |
| `backup1`, `backup2` | Backup entities (sequential numbering) |
| `sun` | Sun entity |
| `wled` | WLED light controller |
| `group` | Group node when node would equal type (e.g., light groups) |

#### Hue Light Groups

Hue light groups should use the same node conventions as regular lights, derived from the group name. The `is_hue_group` attribute in the entity state indicates it's a group. Naming examples:

- **Living Room Main Group**: `aus-lr-main-lightgrp` → `light.aus_lr_main_lightgrp`
- **Garage Main Group**: `aus-gar-main-lightgrp` → `light.aus_gar_main_lightgrp`
- **Master Bath Group**: `aus-mbath-main-lightgrp` → `light.aus_mbath_main_lightgrp`

**Node rules for Hue groups:**
- Strip room words and generic words (`light`, `lights`, `group`, `zone`) from the group name
- If node would be empty or equal to the type, use `group`

**Detection**: Check for `attributes.is_hue_group == true` in entity state to identify Hue groups.

### C. Domain Suffixes (`[type]`)

| Suffix | Domain(s) | Description | Example Use Case |
| :--- | :--- | :--- | :--- |
| `-light` | `light` | Single light control | Living room overhead light |
| `-lightgrp` | `light` | Light group (Hue groups) | Living room main light group |
| `-switch` | `switch` | Switch control | Power outlet, relay switch |
| `-lock` | `lock` | Lock control | Door lock, smart lock |
| `-cam` | `camera` | Camera entity | Security camera, doorbell camera |
| `-speaker` | `media_player` | Speaker / Sonos | Living room Sonos speaker |
| `-sensmot` | `binary_sensor` | Motion sensor | Motion detection binary sensor |
| `-sensocc` | `binary_sensor` | Occupancy sensor | Occupancy detection binary sensor |
| `-sensillum` | `sensor` | Illuminance sensor | Light level measurement (lux) |
| `-sensbatt` | `sensor` | Battery sensor | Battery level percentage |
| `-senstemp` | `sensor` | Temperature sensor | Ambient temperature reading |
| `-humidity` | `sensor` | Humidity sensor | Relative humidity percentage |
| `-mode` | `climate`, `fan`, `cover`, etc. | Mode/state entity | HVAC mode, fan mode, cover position |
| `-brightness` | `light` | Brightness control | Light brightness level (0-255) |
| `-color` | `light` | Color control | RGB color control for lights |
| `-temp` | `climate`, `sensor` | Temperature control/reading | Thermostat setpoint or temperature reading |
| `-inbool` | `input_boolean` | Input boolean helper | Automation helper, virtual switch |
| `-notes` | `input_text` | Editable notes helper | Family or household notes field |
| `-codecount` | `sensor` | Access code count | Kwikset access code count |
| `-usercount` | `sensor` | User count | Kwikset home user count |
| `-lastevent` | `sensor` | Last lock event | Kwikset last lock event |
| `-lastuser` | `sensor` | Last lock user | Kwikset last lock user |
| `-lastmethod` | `sensor` | Last lock method | Kwikset last lock method |
| `-lastcategory` | `sensor` | Last lock category | Kwikset last lock category |

**Exception rule:** If an integration emits a functional sensor that does not map to an existing standard suffix, add a documented suffix here and require explicit reasoning in the rename plan notes or review comments. Kwikset suffixes above are the first approved exception set.

#### Sonos Integration (domain.aus_[room]_sonos_[function])

Sonos entities use `sonos` as the `[node]` segment. The `[type]` describes the **function** using abbreviated no-underscore form (segments may not contain underscores per §2.A rules).

> **Observed deviation**: Some entities use the function directly as the node (e.g. `switch.aus_gar_touchctrl_switch`, node=`touchctrl`) rather than the `sonos` node. Both forms are valid during transition; target is the `_sonos_` pattern.

| Function | Domain | Canonical entity_id | Notes |
| :--- | :--- | :--- | :--- |
| `speaker` | `media_player` | `media_player.aus_{room}_sonos_speaker` | |
| `alarm{N}` | `switch` | `switch.aus_{room}_sonos_alarm1` | One per alarm; created in Sonos app |
| `bass` | `number` | `number.aus_{room}_sonos_bass` | |
| `treble` | `number` | `number.aus_{room}_sonos_treble` | |
| `loudness` | `switch` | `switch.aus_{room}_sonos_loudness` | |
| `crossfade` | `switch` | `switch.aus_{room}_sonos_crossfade` | |
| `nightsound` | `switch` | `switch.aus_{room}_sonos_nightsound` | Home theater only; disabled by default |
| `touchctrl` | `switch` | `switch.aus_{room}_sonos_touchctrl` | All devices; **disabled by default** — enable in Devices & Services |
| `statuslight` | `switch` | `switch.aus_{room}_sonos_statuslight` | All devices; **disabled by default** — enable in Devices & Services |
| `speechenh` | `switch` | `switch.aus_{room}_sonos_speechenh` | Home theater only |

**Pattern:** `domain.aus_[room]_sonos_[function]` — function must be a single lowercase alphanumeric token (no underscores). Do not repeat the domain as a suffix.

**Balance**: Not exposed as a HA entity. Sonos app only.

#### Sonos EQ Dashboard Wildcard Patterns

Because integration-generated entity IDs may use abbreviated or legacy underscore forms before renaming, dashboards must include both forms. Canonical wildcard set for EQ & audio auto-entities cards (substitute `{room}` with `lr`, `gar`, `mbr`, etc.):

```yaml
filter:
  include:
    - entity_id: "*aus_{room}*bass*"
    - entity_id: "*aus_{room}*treble*"
    - entity_id: "*aus_{room}*loudness*"
    - entity_id: "*aus_{room}*crossfade*"
    - entity_id: "*aus_{room}*nightsound*"      # canonical (no underscore)
    - entity_id: "*aus_{room}*night_sound*"     # legacy fallback
    - entity_id: "*aus_{room}*touchctrl*"       # canonical abbreviated form
    - entity_id: "*aus_{room}*touch_control*"   # legacy fallback
    - entity_id: "*aus_{room}*statuslight*"     # canonical abbreviated form
    - entity_id: "*aus_{room}*status_light*"    # legacy fallback
    - entity_id: "*aus_{room}*speech*"          # catches speechenh + legacy speech_enhancement
```

**Rule**: For any multi-word Sonos function, always include BOTH the abbreviated no-underscore form AND the legacy underscore form. See SONOS_INTEGRATION_SPIKES.md Spike 2 for root cause.

## 4. Room Inference and Area Assignment Methodology

This section describes the framework for inferring which room/area a device or entity belongs to, based on metadata and relationships. This methodology is integrated into GenAI entity naming scripts and area assignment automation.

### 4.1 Core Principles

#### Device-Entity Relationship Tracing

Every entity in Home Assistant is linked to a **device** via `device_id`. Entities from the same device share physical location.

```
Device (physical) → Multiple Entities (logical)
     ↓
  Area (room)
```

**Implementation:**
```python
# Group entities by device_id
entities_by_device = defaultdict(list)
for entity in entities:
    did = entity.get("device_id")
    if did:
        entities_by_device[did].append(entity)
```

#### Sibling Context Propagation

If one entity from a device has a known room, ALL entities from that device inherit the same room.

**Example:**
```
Device: TP-Link Power Strip (office)
  └─ switch.aus_ofc_plug1_switch  → room: ofc (known)
  └─ sensor.power_strip_voltage   → room: ofc (inferred from sibling)
```

#### Name-Based Room Inference

Parse device/entity names for room keywords:

| Pattern | Inferred Room Code |
|---------|-------------------|
| `masterbath`, `master bath` | `mbath` |
| `living room`, `family` | `lr` |
| `kitchen`, `undercabinet` | `kit` |
| `office`, `desk` | `ofc` |
| `nursery` | `nur` |
| `garage` | `gar` |
| `front porch` | `fpor` |
| `back porch` | `bpor` |
| `hallway`, `stair` | `hall` |
| `bedroom`, `master bed` | `mbr` |
| `guest bath` | `guestbath` |
| `half bath`, `powder` | `bath3` |

**Implementation:**
```python
def infer_room_from_name(name: str) -> Optional[str]:
    name_lower = name.lower()
    patterns = {
        "masterbath": "mbath",
        "master bath": "mbath",
        "guest bath": "guestbath",
        "half bath": "bath3",
        "living room": "lr",
        "family": "lr",
        "kitchen": "kit",
        "office": "ofc",
        "nursery": "nur",
        "garage": "gar",
        "hallway": "hall",
        "master bed": "mbr",
        "front porch": "fpor",
        "back porch": "bpor",
    }
    for pattern, room in patterns.items():
        if pattern in name_lower:
            return room
    return None
```

#### Manufacturer/Model Context

Certain device types have predictable locations:

| Device Type | Typical Location |
|-------------|------------------|
| Thermostat | Living Room or Master Bedroom |
| Motion Sensor | Hallway, Kitchen, Entry |
| Smart Lock | Entry, Garage Door |
| WLED Strip | Kitchen (undercabinet), Entertainment |
| Bathroom Dimmer | Bathroom (check name for which) |
| Outdoor Light | Porch, Driveway, Backyard |

#### Platform-Based Grouping

Entities from the same integration often share location patterns. For example, all Hue lights from the same bridge can be grouped by name prefix to identify rooms.

#### Combo Device Detection

Some devices combine multiple functions (e.g., dimmer + occupancy):

```python
def is_combo_device(device_entities: List[Dict]) -> Dict[str, bool]:
    """Detect if device has multiple capabilities."""
    capabilities = {
        "has_light": False,
        "has_dimmer": False,
        "has_occupancy": False,
        "has_motion": False,
        "has_temperature": False,
    }
    
    for entity in device_entities:
        eid = entity.get("entity_id", "").lower()
        ename = (entity.get("name") or "").lower()
        
        if eid.startswith("light."):
            capabilities["has_light"] = True
        if "dimmer" in eid or "brightness" in eid:
            capabilities["has_dimmer"] = True
        if "occupancy" in eid or "occupancy" in ename:
            capabilities["has_occupancy"] = True
        if "motion" in eid or eid.startswith("binary_sensor.") and "mot" in eid:
            capabilities["has_motion"] = True
        if "temp" in eid or eid.endswith("_senstemp"):
            capabilities["has_temperature"] = True
    
    return capabilities
```

### 4.2 Bathroom Mapping Example

**Scenario:** A house with multiple bathrooms:
- **Master Bath** (`mbath`): Primary bathroom attached to master bedroom
- **Bathroom 2** (`bath2`): Secondary bathroom (e.g., nursery bath)
- **Bathroom 3** (`bath3`): Half bath / powder room
- **Guest Bath** (`guestbath`): Guest room bathroom

**Inference Process:**

1. **Find all bathroom-related devices:**
   ```python
   bath_keywords = ["bath", "powder", "toilet", "vanity"]
   bath_devices = [d for d in devices 
                   if any(k in d.get("name", "").lower() for k in bath_keywords)]
   ```

2. **Group by naming patterns:**
   - `"masterbath-sl"` → Master Bath
   - `"guest bathroom"` → Guest Bath
   - `"ss guest bathroom"` → Needs clarification (could be either)

3. **Count lights per bathroom:**
   - Bathroom 2 (nursery): 3 Hue + WiZ + Dimmer
   - Bathroom 3 (half): Combo dimmer+occupancy only
   - Master Bath: Hue bulbs

4. **Assign based on device capabilities:**
   - Single combo switch → likely half bath
   - Multiple decorative lights → likely master/guest bath
   - Functional lighting only → likely secondary bath

### 4.3 Integration Points

#### In `genai_entity_namer.py`

Add to `prepare_entity_for_genai()`:
```python
# Include room inference hints
if not entity.get("area_id"):
    inferred_room = infer_room_from_name(entity.get("name", ""))
    if inferred_room:
        base["inferred_room"] = inferred_room
        base["inference_source"] = "name_pattern"
```

#### In `suggest_area_assignments.py`

Use relationship tracing:
```python
def suggest_area_for_device(device, entities, areas):
    # 1. Check name patterns
    inferred = infer_room_from_name(device.get("name", ""))
    if inferred:
        return map_room_code_to_area(inferred)
    
    # 2. Check sibling entities for platform room codes
    for entity in entities:
        eid = entity.get("entity_id", "")
        if "_lr_" in eid: return "Living Room"
        if "_kit_" in eid: return "Kitchen"
        if "_mbath_" in eid: return "Master Bath"
        # ... etc
    
    # 3. Check platform/manufacturer patterns
    # ... etc
```

#### GenAI Prompt Enhancement

Include this context in system prompt:
```
ROOM INFERENCE RULES:
1. Entities from same device_id share the same room
2. If entity name contains room hint, use it
3. If sibling entity has platform room code, propagate it
4. Bathroom mapping: mbath=master, bath2=nursery, bath3=half, guestbath=guest
```

### 4.4 Validation Checklist

- [ ] All entities have an area assigned
- [ ] No entity is in "unknown" area
- [ ] Sibling entities share the same room
- [ ] Name patterns match assigned rooms
- [ ] Combo devices are properly identified
