# DATA_MODEL.md
Last updated: 2026-03-03

## Inventory input schema (CSV)
Required columns
- category (router, camera, lock, light, thermostat, speaker, appliance, sensor, hub, other)
- vendor (manufacturer)
- model (model name or number)

Optional columns
- device_name
- firmware_version
- mac (do not require, do not output by default)
- local_control_possible (yes/no/unknown)
- cloud_required (yes/no/unknown)
- notes

## Normalized device record (internal JSON)
{
  "device_id": "string",
  "source": "ha|csv|manual",
  "category": "camera|router|lock|...",
  "vendor": "string",
  "model": "string",
  "name": "string|null",
  "firmware_version": "string|null",
  "raw": { "any": "metadata" }
}

## Risk register output schema (CSV)
- device_id
- category
- vendor
- model
- risk_score (0-100)
- confidence (high|medium|low)
- data_sensitivity (low|med|high)
- cloud_exposure (local|optional|required|unknown)
- exploitation_signal (none|cve|kev)
- top_cves (semicolon-separated CVE IDs)
- reasons (short bullets separated by "; ")
- recommendation (keep|keep_with_mitigations|replace|investigate)

## Run metadata (JSON)
- run_id
- timestamp_utc
- inputs_used (ha/csv)
- api_calls:
  - nvd_count
  - kev_fetch
- cache_hits:
  - nvd
  - kev
- version
