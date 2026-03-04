"""Generate artifact files."""

import csv
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from leakprint import __version__
from leakprint.models import ScoredDevice


def write_risk_register(scored: list[ScoredDevice], path: Path) -> None:
    """Write device_risk_register.csv."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "device_id", "category", "vendor", "model", "risk_score", "confidence",
            "data_sensitivity", "cloud_exposure", "exploitation_signal",
            "top_cves", "reasons", "recommendation",
        ])
        for s in scored:
            w.writerow([
                s.device.device_id,
                s.device.category,
                s.device.vendor,
                s.device.model,
                s.risk_score,
                s.confidence,
                s.data_sensitivity,
                s.cloud_exposure,
                s.exploitation_signal,
                ";".join(s.cve_ids[:10]),
                "; ".join(s.reasons),
                s.recommendation,
            ])


def write_risk_report(scored: list[ScoredDevice], path: Path) -> None:
    """Write risk_report.md."""
    path.parent.mkdir(parents=True, exist_ok=True)
    sorted_devices = sorted(scored, key=lambda s: s.risk_score, reverse=True)
    top5 = sorted_devices[:5]

    lines = [
        "# Risk Report",
        "",
        "## Top 5 by Risk",
        "",
    ]
    for s in top5:
        lines.append(f"- **{s.device.vendor} {s.device.model}** ({s.device.category})")
        lines.append(f"  - Score: {s.risk_score} | Confidence: {s.confidence}")
        lines.append(f"  - Recommendation: {s.recommendation}")
        if s.cve_ids:
            lines.append(f"  - CVEs: {', '.join(s.cve_ids[:5])}")
        lines.append("")

    lines.extend([
        "## Quick Wins",
        "",
        "- Ensure devices are on latest firmware where possible",
        "- Disable cloud features when local control is available",
        "- Use strong, unique passwords for vendor accounts",
        "- Segment IoT devices on a separate network if feasible",
        "",
        "## Replacements",
        "",
    ])
    replace = [s for s in scored if s.recommendation == "replace"]
    if replace:
        for s in replace:
            reason = "; ".join(s.reasons)
            lines.append(f"- **{s.device.vendor} {s.device.model}**: {reason}")
    else:
        lines.append("No devices flagged for replacement at this time.")
    lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def write_blueprint(scored: list[ScoredDevice], path: Path) -> None:
    """Write blueprint.md template."""
    path.parent.mkdir(parents=True, exist_ok=True)
    high_risk = sum(1 for s in scored if s.risk_score >= 60)
    content = f"""# Smart Home Blueprint

## Goals and Constraints
<!-- Define your goals (privacy, reliability, cost) and constraints -->

## Phased Backlog
<!-- Define phases: foundation, core devices, enhancements -->

## Risk Register Findings
This blueprint references findings from the device risk register:
- {len(scored)} devices assessed
- {high_risk} devices with elevated risk (score >= 60)

See `device_risk_register.csv` for details.
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def write_mitigation_plan(scored: list[ScoredDevice], path: Path) -> None:
    """Write mitigation_plan.md."""
    path.parent.mkdir(parents=True, exist_ok=True)
    mitigate = [s for s in scored if s.recommendation == "keep_with_mitigations"]
    replace = [s for s in scored if s.recommendation == "replace"]

    lines = [
        "# Mitigation Plan",
        "",
        "## Immediate Actions",
        "",
        "- Review devices with KEV matches; prioritize updates or replacement",
        "- Disable unnecessary cloud features",
        "- Enable MFA on vendor accounts where available",
        "",
        "## Devices Requiring Mitigation",
        "",
    ]
    for s in mitigate:
        lines.append(f"- **{s.device.vendor} {s.device.model}**: {'; '.join(s.reasons)}")
    if not mitigate:
        lines.append("None identified.")
    lines.append("")
    lines.append("## Recommended Replacements")
    lines.append("")
    for s in replace:
        lines.append(f"- **{s.device.vendor} {s.device.model}**: {'; '.join(s.reasons)}")
    if not replace:
        lines.append("None identified.")
    lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def write_run_metadata(
    path: Path,
    inputs_used: str,
    device_count: int,
    nvd_count: int,
    kev_fetch: bool,
    nvd_cache_hits: int,
    kev_cache_hit: bool,
) -> None:
    """Write run_metadata.json."""
    path.parent.mkdir(parents=True, exist_ok=True)
    meta = {
        "run_id": str(uuid.uuid4()),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "inputs_used": inputs_used,
        "device_count": device_count,
        "api_calls": {"nvd_count": nvd_count, "kev_fetch": 1 if kev_fetch else 0},
        "cache_hits": {"nvd": nvd_cache_hits, "kev": 1 if kev_cache_hit else 0},
        "version": __version__,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
