"""Pipeline orchestration."""

import json
from pathlib import Path

from leakprint.ingest import ingest_csv, ingest_from_ha
from leakprint.enrich import KEVClient, NVDClient
from leakprint.match import build_search_queries
from leakprint.models import Device, EnrichedDevice
from leakprint.scoring import score_device
from leakprint.reporting import (
    write_risk_register,
    write_risk_report,
    write_blueprint,
    write_mitigation_plan,
    write_run_metadata,
)


def _load_inventory(out_dir: Path) -> list[Device]:
    path = out_dir / "inventory.normalized.json"
    if not path.exists():
        return []
    with open(path) as f:
        data = json.load(f)
    return [
        Device(
            device_id=d["device_id"],
            source=d["source"],
            category=d["category"],
            vendor=d["vendor"],
            model=d["model"],
            name=d.get("name"),
            firmware_version=d.get("firmware_version"),
            cloud_required=d.get("cloud_required"),
            raw=d.get("raw", {}),
        )
        for d in data
    ]


def _save_inventory(devices: list[Device], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "inventory.normalized.json", "w") as f:
        json.dump([d.to_dict() for d in devices], f, indent=2)


def ingest_only(
    inventory_path: Path | None = None,
    from_ha: bool = False,
    out_dir: Path = Path("artifacts"),
) -> list[Device]:
    """Ingest only. Writes inventory.normalized.json."""
    if from_ha:
        devices = ingest_from_ha()
    elif inventory_path:
        devices = ingest_csv(inventory_path)
    else:
        raise ValueError("Provide --inventory or --from-ha")
    _save_inventory(devices, out_dir)
    return devices


def enrich_only(
    out_dir: Path = Path("artifacts"),
    cache_dir: Path = Path("cache"),
    max_nvd_results: int = 20,
    kev_ttl_hours: int = 24,
) -> tuple[list[EnrichedDevice], dict]:
    """Enrich from inventory.normalized.json. Returns enriched devices and stats."""
    devices = _load_inventory(out_dir)
    if not devices:
        raise FileNotFoundError(
            "No inventory found. Run 'leakprint ingest' first."
        )

    kev = KEVClient(cache_dir, kev_ttl_hours)
    kev_was_cached = (cache_dir / "kev.json").exists() and not kev._is_expired()
    kev_set = kev.get_cve_set()

    nvd = NVDClient(cache_dir)
    nvd_count = 0
    nvd_cache_hits = 0

    enriched: list[EnrichedDevice] = []
    for device in devices:
        queries = build_search_queries(device)
        all_cves: list[str] = []
        for q in queries:
            if not q.strip():
                continue
            cache_path = nvd._cache_path(f"kw_{q}_{max_nvd_results}")
            if cache_path.exists():
                nvd_cache_hits += 1
                with open(cache_path) as f:
                    data = json.load(f)
                all_cves.extend(data.get("cve_ids", []))
            else:
                cves = nvd.search_cves(q, max_nvd_results)
                nvd_count += 1
                all_cves.extend(cves)
            if len(all_cves) >= max_nvd_results:
                break

        # Dedupe, preserve order
        seen = set()
        unique = []
        for c in all_cves:
            if c not in seen:
                seen.add(c)
                unique.append(c)
            if len(unique) >= max_nvd_results:
                break

        kev_matched = any(c in kev_set for c in unique)
        enriched.append(
            EnrichedDevice(device=device, cve_ids=unique, kev_matched=kev_matched)
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "enrichment.json", "w") as f:
        json.dump(
            [
                {
                    "device_id": e.device.device_id,
                    "cve_ids": e.cve_ids,
                    "kev_matched": e.kev_matched,
                }
                for e in enriched
            ],
            f,
            indent=2,
        )

    stats = {
        "nvd_count": nvd_count,
        "nvd_cache_hits": nvd_cache_hits,
        "kev_fetch": not kev_was_cached,
        "kev_cache_hit": kev_was_cached,
    }
    return enriched, stats


def score_only(out_dir: Path = Path("artifacts")) -> list:
    """Score from enrichment.json. Returns ScoredDevice list."""
    inv_path = out_dir / "inventory.normalized.json"
    enr_path = out_dir / "enrichment.json"
    if not inv_path.exists() or not enr_path.exists():
        raise FileNotFoundError(
            "Missing inventory.normalized.json or enrichment.json. Run ingest and enrich first."
        )

    with open(inv_path) as f:
        inv_data = json.load(f)
    with open(enr_path) as f:
        enr_data = json.load(f)

    by_id = {d["device_id"]: d for d in inv_data}
    scored = []
    for e in enr_data:
        did = e["device_id"]
        if did not in by_id:
            continue
        d = by_id[did]
        device = Device(
            device_id=d["device_id"],
            source=d["source"],
            category=d["category"],
            vendor=d["vendor"],
            model=d["model"],
            name=d.get("name"),
            firmware_version=d.get("firmware_version"),
            cloud_required=d.get("cloud_required"),
            raw=d.get("raw", {}),
        )
        enriched = EnrichedDevice(
            device=device,
            cve_ids=e.get("cve_ids", []),
            kev_matched=e.get("kev_matched", False),
        )
        scored.append(score_device(device, enriched))

    with open(out_dir / "scored.json", "w") as f:
        json.dump(
            [
                {
                    "device_id": s.device.device_id,
                    "risk_score": s.risk_score,
                    "confidence": s.confidence,
                    "recommendation": s.recommendation,
                    "reasons": s.reasons,
                    "cve_ids": s.cve_ids,
                }
                for s in scored
            ],
            f,
            indent=2,
        )
    return scored


def _load_scored_devices(out_dir: Path) -> list:
    """Load ScoredDevice list from inventory + enrichment + scored.json."""
    from leakprint.models import Device, EnrichedDevice, ScoredDevice
    from leakprint.scoring import score_device

    inv_path = out_dir / "inventory.normalized.json"
    enr_path = out_dir / "enrichment.json"
    scored_path = out_dir / "scored.json"
    if not all(p.exists() for p in [inv_path, enr_path, scored_path]):
        raise FileNotFoundError(
            "Missing pipeline artifacts. Run full pipeline first."
        )

    with open(inv_path) as f:
        inv_data = json.load(f)
    with open(enr_path) as f:
        enr_data = json.load(f)

    by_id = {d["device_id"]: d for d in inv_data}
    enr_by_id = {e["device_id"]: e for e in enr_data}

    scored_devices = []
    for did, d in by_id.items():
        e = enr_by_id.get(did, {})
        device = Device(
            device_id=d["device_id"],
            source=d["source"],
            category=d["category"],
            vendor=d["vendor"],
            model=d["model"],
            name=d.get("name"),
            firmware_version=d.get("firmware_version"),
            cloud_required=d.get("cloud_required"),
            raw=d.get("raw", {}),
        )
        enriched = EnrichedDevice(
            device=device,
            cve_ids=e.get("cve_ids", []),
            kev_matched=e.get("kev_matched", False),
        )
        scored_devices.append(score_device(device, enriched))

    return scored_devices


def report_only(out_dir: Path = Path("artifacts")) -> None:
    """Generate reports from scored.json."""
    scored_devices = _load_scored_devices(out_dir)

    write_risk_register(scored_devices, out_dir / "device_risk_register.csv")
    write_risk_report(scored_devices, out_dir / "risk_report.md")
    write_blueprint(scored_devices, out_dir / "blueprint.md")
    write_mitigation_plan(scored_devices, out_dir / "mitigation_plan.md")

    meta_path = out_dir / "run_metadata.json"
    if meta_path.exists():
        with open(meta_path) as f:
            meta = json.load(f)
        write_run_metadata(
            meta_path,
            inputs_used=meta.get("inputs_used", "unknown"),
            device_count=len(scored_devices),
            nvd_count=meta.get("api_calls", {}).get("nvd_count", 0),
            kev_fetch=meta.get("api_calls", {}).get("kev_fetch", 0) == 1,
            nvd_cache_hits=meta.get("cache_hits", {}).get("nvd", 0),
            kev_cache_hit=meta.get("cache_hits", {}).get("kev", 0) == 1,
        )
    else:
        write_run_metadata(
            meta_path,
            inputs_used="unknown",
            device_count=len(scored_devices),
            nvd_count=0,
            kev_fetch=False,
            nvd_cache_hits=0,
            kev_cache_hit=False,
        )


def run_pipeline(
    inventory_path: Path | None = None,
    from_ha: bool = False,
    out_dir: Path = Path("artifacts"),
    cache_dir: Path = Path("cache"),
    max_nvd_results: int = 20,
    kev_ttl_hours: int = 24,
) -> None:
    """Run full pipeline: ingest → enrich → score → report."""
    # Ingest
    if from_ha:
        try:
            devices = ingest_from_ha()
        except (ValueError, RuntimeError) as e:
            if inventory_path:
                # Degrade: try CSV
                devices = ingest_csv(inventory_path)
            else:
                raise e
    elif inventory_path:
        devices = ingest_csv(inventory_path)
    else:
        raise ValueError("Provide --inventory or --from-ha")

    _save_inventory(devices, out_dir)
    inputs_used = "ha" if from_ha and devices else "csv"

    # Enrich
    enriched, stats = enrich_only(
        out_dir=out_dir,
        cache_dir=cache_dir,
        max_nvd_results=max_nvd_results,
        kev_ttl_hours=kev_ttl_hours,
    )

    # Score
    scored = score_only(out_dir=out_dir)

    # Report
    write_risk_register(scored, out_dir / "device_risk_register.csv")
    write_risk_report(scored, out_dir / "risk_report.md")
    write_blueprint(scored, out_dir / "blueprint.md")
    write_mitigation_plan(scored, out_dir / "mitigation_plan.md")
    write_run_metadata(
        out_dir / "run_metadata.json",
        inputs_used=inputs_used,
        device_count=len(scored),
        nvd_count=stats["nvd_count"],
        kev_fetch=stats["kev_fetch"],
        nvd_cache_hits=stats["nvd_cache_hits"],
        kev_cache_hit=stats["kev_cache_hit"],
    )
