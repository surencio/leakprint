# ARCHITECTURE.md
Last updated: 2026-03-03

## Overview
Leakprint is a CLI tool that ingests smart home device inventory, enriches it with vulnerability data, scores risk, and produces artifact files.

## Pipeline stages
1. **Ingest** – Load inventory from CSV or Home Assistant WebSocket
2. **Enrich** – Fetch KEV catalog and query NVD for CVEs
3. **Match** – Map devices to CVEs via keyword search
4. **Score** – Apply risk rubric and confidence
5. **Report** – Generate artifact files

## Data flow
```
[CSV | HA] → inventory.normalized.json → enrichment.json → scored.json → artifacts/
```

## Caching
- File-based cache in `--cache` directory
- KEV: TTL configurable (default 24h)
- NVD: Keyed by query string, no TTL (persistent)

## Env vars
- HASS_URL, HASS_TOKEN – Home Assistant
- NVD_API_KEY – Optional, improves rate limits
