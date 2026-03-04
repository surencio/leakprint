# API_INTEGRATIONS.md
Last updated: 2026-03-03

## 1) Home Assistant WebSocket API
Home Assistant exposes a WebSocket API at `/api/websocket` and uses an auth handshake:
- server sends auth_required
- client sends auth with token
- server sends auth_ok

Device inventory command:
- type: "config/device_registry/list"

Implementation notes
- Inputs:
  - HASS_URL (example: http://homeassistant.local:8123)
  - HASS_TOKEN (Long-Lived Access Token)
- Connect to: {HASS_URL}/api/websocket
- Send:
  - {"type": "auth", "access_token": "..."}
  - {"id": 1, "type": "config/device_registry/list"}

## 2) NVD CVE API
Endpoint examples:
- https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=CVE-2019-1010218
- keywordSearch queries supported.

Rate limits
- without API key: 5 requests per rolling 30 seconds
- with API key: 50 requests per rolling 30 seconds

Implementation notes
- Inputs:
  - NVD_API_KEY (optional)
- Use backoff and caching. Avoid repeated lookups.
- Prefer querying by keywordSearch and limiting resultsPerPage.

## 3) CISA KEV catalog data
CISA publishes Known Exploited Vulnerabilities data, mirrored in cisagov/kev-data.

Implementation notes
- Default fetch URL (GitHub raw):
  https://raw.githubusercontent.com/cisagov/kev-data/develop/known_exploited_vulnerabilities.json
- Cache locally (cache/kev.json) with TTL (example: 24 hours)
