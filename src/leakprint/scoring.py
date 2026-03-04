"""Risk scoring per docs/SCORING.md."""

from leakprint.models import Device, EnrichedDevice, ScoredDevice

# Base scores by category sensitivity
CATEGORY_BASE: dict[str, int] = {
    "router": 35,
    "camera": 40,
    "lock": 35,
    "light": 10,
    "thermostat": 25,
    "speaker": 35,  # mic/voice assistant
    "hub": 25,
    "sensor": 10,
    "appliance": 10,
    "other": 15,
}

# Cloud exposure modifiers
CLOUD_MODIFIER: dict[str | None, int] = {
    "required": 20,
    "yes": 20,
    "optional": 10,
    "no": 0,
    "local": 0,
    "unknown": 10,
    None: 10,
}

# Exploitation signal
EXPLOITATION_MODIFIER = {"kev": 30, "cve": 15, "none": 0}

# Update posture (MVP: mostly unknown)
UPDATE_MODIFIER = {"eol": 15, "unknown": 10, "supported": 0}

# Data sensitivity for output
CATEGORY_SENSITIVITY: dict[str, str] = {
    "router": "high",
    "camera": "high",
    "lock": "high",
    "speaker": "high",
    "thermostat": "med",
    "hub": "med",
    "light": "low",
    "sensor": "low",
    "appliance": "low",
    "other": "med",
}


def _cloud_exposure(device: Device) -> str:
    """Map device to cloud_exposure value."""
    cr = (device.cloud_required or "unknown").lower()
    if cr in ("yes", "required"):
        return "required"
    if cr in ("no", "local"):
        return "local"
    if cr == "optional":
        return "optional"
    return "unknown"


def _exploitation_signal(kev_matched: bool, has_cves: bool) -> str:
    if kev_matched:
        return "kev"
    if has_cves:
        return "cve"
    return "none"


def _confidence(
    has_vendor: bool,
    has_model: bool,
    has_cves: bool,
    kev_matched: bool,
) -> str:
    if has_vendor and has_model and (has_cves or kev_matched):
        return "high"
    if has_vendor and has_cves:
        return "medium"
    return "low"


def _recommendation(score: int, confidence: str) -> str:
    if confidence == "low" and score >= 50:
        return "investigate"
    if score >= 80 and confidence in ("high", "medium"):
        return "replace"
    if 40 <= score < 80:
        return "keep_with_mitigations"
    return "keep"


def score_device(device: Device, enriched: EnrichedDevice) -> ScoredDevice:
    """Compute risk score and recommendation for a device."""
    base = CATEGORY_BASE.get(device.category, 15)
    cloud = CLOUD_MODIFIER.get(
        (device.cloud_required or "unknown").lower(),
        CLOUD_MODIFIER[None],
    )
    exploitation = _exploitation_signal(enriched.kev_matched, bool(enriched.cve_ids))
    expl_mod = EXPLOITATION_MODIFIER[exploitation]
    update = UPDATE_MODIFIER["unknown"]  # MVP: assume unknown

    raw_score = base + cloud + expl_mod + update
    risk_score = max(0, min(100, raw_score))

    has_vendor = device.vendor and device.vendor != "unknown"
    has_model = device.model and device.model != "unknown"
    confidence = _confidence(
        has_vendor, has_model, bool(enriched.cve_ids), enriched.kev_matched
    )
    recommendation = _recommendation(risk_score, confidence)

    reasons: list[str] = []
    if base >= 25:
        reasons.append(f"High-sensitivity category ({device.category})")
    if cloud >= 10:
        reasons.append(f"Cloud exposure: {_cloud_exposure(device)}")
    if exploitation == "kev":
        reasons.append("Known exploited vulnerability (KEV)")
    elif exploitation == "cve":
        reasons.append(f"{len(enriched.cve_ids)} CVE(s) found")
    if confidence == "low":
        reasons.append("Low confidence (limited model match)")

    return ScoredDevice(
        device=device,
        cve_ids=enriched.cve_ids,
        kev_matched=enriched.kev_matched,
        risk_score=risk_score,
        confidence=confidence,
        data_sensitivity=CATEGORY_SENSITIVITY.get(device.category, "med"),
        cloud_exposure=_cloud_exposure(device),
        exploitation_signal=exploitation,
        reasons=reasons,
        recommendation=recommendation,
    )
