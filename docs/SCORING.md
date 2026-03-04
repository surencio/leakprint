# SCORING.md
Last updated: 2026-03-03

## Goals
- Make risk explainable.
- Prefer conservative outputs over false precision.
- Provide a confidence score.

## Risk score (0-100)
Start with base score from category sensitivity:
- router: 35
- camera/doorbell cam: 40
- microphone/voice assistant: 35
- lock/garage: 35
- thermostat: 25
- hub/bridge: 25
- lights/plugs: 10
- appliance: 10
Then add modifiers:

Cloud exposure
- required cloud: +20
- optional cloud: +10
- local only: +0
- unknown: +10

Exploitation signal
- KEV match: +30
- CVE match (no KEV): +15
- none: +0

Update posture
- EOL known: +15
- unknown: +10
- supported: +0

Mitigations (if user indicates)
- local-only mode enabled: -10
- on isolated VLAN: -10
- MFA enabled on vendor account: -5

Clamp to 0-100.

## Confidence
High
- Exact vendor+model match and direct CVE/KEV evidence
Medium
- Vendor match and keyword evidence
Low
- Category-only inference or "unknown model"

## Recommendation logic
Replace
- risk_score >= 80 and confidence >= medium
Keep with mitigations
- risk_score 40-79
Keep
- risk_score < 40
Investigate
- confidence low and risk_score >= 50
