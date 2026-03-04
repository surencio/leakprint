"""Tests for scoring."""

import pytest

from leakprint.models import Device, EnrichedDevice
from leakprint.scoring import score_device


def test_scoring_clamps_to_0_100():
    device = Device("x", "csv", "light", "philips", "hue")
    # No CVEs, low sensitivity
    enriched = EnrichedDevice(device=device, cve_ids=[], kev_matched=False)
    scored = score_device(device, enriched)
    assert 0 <= scored.risk_score <= 100

    # KEV match on camera - could push high
    device_high = Device("y", "csv", "camera", "wyze", "cam v3")
    enriched_high = EnrichedDevice(
        device=device_high, cve_ids=["CVE-2024-1234"], kev_matched=True
    )
    scored_high = score_device(device_high, enriched_high)
    assert 0 <= scored_high.risk_score <= 100


def test_kev_match_increases_score():
    device = Device("x", "csv", "camera", "wyze", "cam")
    no_kev = EnrichedDevice(device=device, cve_ids=["CVE-2024-1"], kev_matched=False)
    with_kev = EnrichedDevice(device=device, cve_ids=["CVE-2024-1"], kev_matched=True)
    s_no = score_device(device, no_kev)
    s_yes = score_device(device, with_kev)
    assert s_yes.risk_score > s_no.risk_score
    assert s_yes.exploitation_signal == "kev"
    assert s_no.exploitation_signal == "cve"
