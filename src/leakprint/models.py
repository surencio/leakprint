"""Data models for Leakprint."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Device:
    """Normalized device record."""

    device_id: str
    source: str  # ha | csv | manual
    category: str
    vendor: str
    model: str
    name: str | None = None
    firmware_version: str | None = None
    cloud_required: str | None = None  # yes | no | unknown
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "source": self.source,
            "category": self.category,
            "vendor": self.vendor,
            "model": self.model,
            "name": self.name,
            "firmware_version": self.firmware_version,
            "cloud_required": self.cloud_required,
            "raw": self.raw,
        }


@dataclass
class EnrichedDevice:
    """Device with CVE enrichment."""

    device: Device
    cve_ids: list[str] = field(default_factory=list)
    kev_matched: bool = False


@dataclass
class ScoredDevice:
    """Device with risk score and recommendation."""

    device: Device
    cve_ids: list[str]
    kev_matched: bool
    risk_score: int
    confidence: str  # high | medium | low
    data_sensitivity: str  # low | med | high
    cloud_exposure: str  # local | optional | required | unknown
    exploitation_signal: str  # none | cve | kev
    reasons: list[str]
    recommendation: str  # keep | keep_with_mitigations | replace | investigate
