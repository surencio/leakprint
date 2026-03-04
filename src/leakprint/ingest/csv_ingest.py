"""CSV inventory ingestion."""

import csv
import hashlib
import json
from pathlib import Path

from leakprint.models import Device
from leakprint.match import normalize_vendor, normalize_model

REQUIRED_COLUMNS = {"category", "vendor", "model"}
VALID_CATEGORIES = {
    "router", "camera", "lock", "light", "thermostat", "speaker",
    "appliance", "sensor", "hub", "other"
}
OPTIONAL_COLUMNS = {
    "device_name", "firmware_version", "mac",
    "local_control_possible", "cloud_required", "notes"
}


def _validate_row(row: dict[str, str], row_num: int) -> list[str]:
    """Validate a CSV row. Returns list of error messages."""
    errors: list[str] = []
    for col in REQUIRED_COLUMNS:
        if col not in row or not str(row.get(col, "")).strip():
            errors.append(f"Row {row_num}: missing required column '{col}'")
    if row.get("category", "").strip().lower() not in VALID_CATEGORIES:
        errors.append(f"Row {row_num}: invalid category '{row.get('category')}'")
    return errors


def _row_to_device(row: dict[str, str], idx: int, source: str = "csv") -> Device:
    """Convert CSV row to Device."""
    vendor = str(row.get("vendor", "")).strip() or "unknown"
    model = str(row.get("model", "")).strip() or "unknown"
    category = str(row.get("category", "")).strip().lower() or "other"

    # device_id: deterministic hash of vendor+model+idx
    raw_id = f"{vendor}|{model}|{idx}"
    device_id = hashlib.sha256(raw_id.encode()).hexdigest()[:16]

    cloud_required = None
    cr = str(row.get("cloud_required", "")).strip().lower()
    if cr in ("yes", "no", "unknown", "optional"):
        cloud_required = cr

    return Device(
        device_id=device_id,
        source=source,
        category=category,
        vendor=normalize_vendor(vendor),
        model=normalize_model(model),
        name=str(row.get("device_name", "")).strip() or None,
        firmware_version=str(row.get("firmware_version", "")).strip() or None,
        cloud_required=cloud_required,
        raw={k: v for k, v in row.items() if k not in ("mac",)},
    )


def ingest_csv(path: Path) -> list[Device]:
    """Ingest devices from CSV. Raises ValueError on schema errors."""
    if not path.exists():
        raise FileNotFoundError(f"Inventory file not found: {path}")

    devices: list[Device] = []
    errors: list[str] = []

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV has no headers")
        headers = {h.strip().lower() for h in (reader.fieldnames or [])}
        missing = REQUIRED_COLUMNS - headers
        if missing:
            raise ValueError(f"CSV missing required columns: {missing}")

        for i, row in enumerate(reader, start=2):  # 1-based, row 1 is header
            # Normalize keys
            normalized = {k.strip().lower(): v for k, v in row.items()}
            errs = _validate_row(normalized, i)
            if errs:
                errors.extend(errs)
                continue
            devices.append(_row_to_device(normalized, i))

    if errors:
        raise ValueError("CSV validation failed:\n" + "\n".join(errors))

    return devices
