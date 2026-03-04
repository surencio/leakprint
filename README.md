# Leakprint

Blueprint + Risk Register for smart homes.

## What it does

Leakprint takes a home's device inventory and produces:

- **Smart Home Blueprint** – plan and sequence
- **Device Risk Register** – privacy and security exposure
- **Mitigation plan** – quick wins, keep vs replace

## What it does not do

- It is not a vulnerability scanner.
- It is not legal advice.
- It will mark unknowns as unknown.

## Quickstart

1. Create a virtual environment and install:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # On Windows: .venv\Scripts\activate
   pip install -e .
   ```

   Or use pipx for a global install:

   ```bash
   pipx install -e .
   ```

2. Create an inventory CSV (see `examples/inventory.csv`).

3. Run:

   ```bash
   leakprint run --inventory examples/inventory.csv --out artifacts/
   ```

### Optional: Home Assistant

If you have Home Assistant, set `HASS_URL` and `HASS_TOKEN` and run:

```bash
leakprint run --from-ha --out artifacts/
```

### Optional: NVD API key

For higher NVD rate limits, set `NVD_API_KEY`:

```bash
export NVD_API_KEY=your-key
leakprint run --inventory examples/inventory.csv --out artifacts/
```

## CLI commands

| Command | Description |
|---------|-------------|
| `leakprint run` | Full pipeline: ingest → enrich → score → report |
| `leakprint ingest` | Ingest from CSV or Home Assistant |
| `leakprint enrich` | Enrich with KEV and NVD data |
| `leakprint score` | Score devices and produce risk register |
| `leakprint report` | Generate report artifacts |

## Options

- `--inventory`, `-i` – Path to inventory CSV
- `--from-ha` – Ingest from Home Assistant (uses `HASS_URL`, `HASS_TOKEN`)
- `--out`, `-o` – Output directory (default: `artifacts/`)
- `--cache`, `-c` – Cache directory (default: `cache/`)
- `--max-nvd-results` – Max CVE results per device (default: 20)
- `--kev-ttl-hours` – KEV cache TTL in hours (default: 24)

## Environment variables

- `HASS_URL` – Home Assistant URL (e.g. `http://homeassistant.local:8123`)
- `HASS_TOKEN` – Long-lived access token for Home Assistant
- `NVD_API_KEY` – Optional; improves NVD rate limits

## Outputs

- `artifacts/device_risk_register.csv`
- `artifacts/risk_report.md`
- `artifacts/blueprint.md`
- `artifacts/mitigation_plan.md`
- `artifacts/run_metadata.json`

## Privacy and safety

- Leakprint does not upload your inventory to third parties.
- MAC addresses and unique identifiers are not output by default.
- Tokens and secrets are read from environment variables only; never hardcoded.
- Public datasets (KEV, NVD) are cached locally to limit API calls.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
