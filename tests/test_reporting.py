"""Tests for report generation."""

import tempfile
from pathlib import Path

from leakprint.models import Device, EnrichedDevice, ScoredDevice
from leakprint.reporting import (
    write_risk_register,
    write_risk_report,
    write_blueprint,
    write_mitigation_plan,
)


def _make_scored():
    device = Device("abc123", "csv", "camera", "wyze", "cam v3")
    return ScoredDevice(
        device=device,
        cve_ids=["CVE-2024-1234"],
        kev_matched=False,
        risk_score=65,
        confidence="high",
        data_sensitivity="high",
        cloud_exposure="optional",
        exploitation_signal="cve",
        reasons=["High-sensitivity category (camera)", "1 CVE(s) found"],
        recommendation="keep_with_mitigations",
    )


def test_report_generation_produces_files():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        scored = [_make_scored()]

        write_risk_register(scored, out / "device_risk_register.csv")
        write_risk_report(scored, out / "risk_report.md")
        write_blueprint(scored, out / "blueprint.md")
        write_mitigation_plan(scored, out / "mitigation_plan.md")

        assert (out / "device_risk_register.csv").exists()
        assert (out / "risk_report.md").exists()
        assert (out / "blueprint.md").exists()
        assert (out / "mitigation_plan.md").exists()

        content = (out / "device_risk_register.csv").read_text()
        assert "wyze" in content
        assert "65" in content

        report = (out / "risk_report.md").read_text()
        assert "Top 5" in report
        assert "Quick Wins" in report
