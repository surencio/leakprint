"""Tests for KEV match detection."""

from leakprint.models import Device, EnrichedDevice
from leakprint.scoring import score_device


def test_kev_match_detection():
    device = Device("x", "csv", "router", "vendor", "model")
    enriched_kev = EnrichedDevice(
        device=device, cve_ids=["CVE-2024-1234"], kev_matched=True
    )
    enriched_no_kev = EnrichedDevice(
        device=device, cve_ids=["CVE-2024-1234"], kev_matched=False
    )

    scored_kev = score_device(device, enriched_kev)
    scored_no_kev = score_device(device, enriched_no_kev)

    assert scored_kev.exploitation_signal == "kev"
    assert scored_no_kev.exploitation_signal == "cve"
    assert scored_kev.risk_score > scored_no_kev.risk_score
