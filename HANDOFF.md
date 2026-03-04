# Leakprint Handoff

**Last updated:** 2026-03-03

## Current state

- **MVP:** Complete and runnable
- **Git:** No commits yet; all files untracked on `main`
- **Tests:** 22 passing

## What's done

- CLI (`leakprint run`, `ingest`, `enrich`, `score`, `report`)
- CSV ingestion with schema validation
- Home Assistant WebSocket ingestion (`config/device_registry/list`)
- KEV client (CISA catalog, 24h cache)
- NVD client (keyword search, rate limits, backoff, file cache)
- Matching (vendor+model → NVD → KEV)
- Scoring per `docs/SCORING.md`
- Artifacts: risk register CSV, risk_report.md, blueprint.md, mitigation_plan.md, run_metadata.json

## Known / pending

- **NVD API key:** Requested; can take 7+ days. Until then: 5 req/30s limit; first run ~2–3 min, cached runs faster.
- **Secrets:** ~~Done.~~ `secrets.yaml` loader added (`--secrets` CLI flag, `LEAKPRINT_SECRETS_PATH` env var, or auto-detect `./secrets.yaml`). Env vars take precedence. Supports `hass_url`, `hass_token`, `nvd_api_key`.

## How to run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
leakprint run --inventory examples/inventory.csv --out artifacts/
```

With Home Assistant (via secrets.yaml):

```bash
# Create secrets.yaml with hass_url, hass_token, nvd_api_key
leakprint run --from-ha --out artifacts/
```

Or via env vars:

```bash
export HASS_URL=http://homeassistant.local:8123
export HASS_TOKEN=your-long-lived-token
leakprint run --from-ha --out artifacts/
```

## Suggested commits

1. `docs: leakprint PRD and specs`
2. `feat: cli and pipeline skeleton`
3. `feat: ingestion (csv + ha websocket)`
4. `feat: enrichment (kev + nvd) with caching`
5. `feat: scoring + reports`
6. `test: minimal unit tests + examples`

## Repo layout

```
src/leakprint/
  cli.py          # Typer commands
  pipeline.py     # Orchestration
  models.py       # Device, EnrichedDevice, ScoredDevice
  match.py        # Normalization, search query builder
  scoring.py      # Risk rubric
  reporting.py   # Artifact writers
  secrets.py     # YAML secrets loader
  ingest/        # csv_ingest, ha_ws_ingest
  enrich/        # kev_client, nvd_client
```
