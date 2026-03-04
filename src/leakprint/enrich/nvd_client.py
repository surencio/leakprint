"""NVD CVE API client with rate limiting and cache."""

import json
import os
import time
from pathlib import Path

import httpx

NVD_BASE = "https://services.nvd.nist.gov/rest/json/cves/2.0"

# Rate limits: 5/30s without key, 50/30s with key
RATE_LIMIT_WINDOW = 30
REQUESTS_NO_KEY = 5
REQUESTS_WITH_KEY = 50


class NVDClient:
    """Query NVD CVE API with backoff and file cache."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.api_key = os.environ.get("NVD_API_KEY", "")
        self._request_times: list[float] = []
        self._max_requests = REQUESTS_WITH_KEY if self.api_key else REQUESTS_NO_KEY

    def _cache_path(self, query: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in query)
        return self.cache_dir / f"nvd_{safe[:80]}.json"

    def _rate_limit(self) -> None:
        """Enforce rate limit."""
        now = time.monotonic()
        self._request_times = [t for t in self._request_times if now - t < RATE_LIMIT_WINDOW]
        if len(self._request_times) >= self._max_requests:
            sleep_time = RATE_LIMIT_WINDOW - (now - self._request_times[0])
            if sleep_time > 0:
                time.sleep(sleep_time)
            self._request_times = []
        self._request_times.append(time.monotonic())

    def _request_with_retry(self, url: str, params: dict) -> dict:
        """Request with exponential backoff."""
        headers = {}
        if self.api_key:
            headers["apiKey"] = self.api_key

        last_err = None
        for attempt in range(4):
            self._rate_limit()
            try:
                resp = httpx.get(url, params=params, headers=headers, timeout=30)
                if resp.status_code == 403:
                    raise RuntimeError("NVD rate limit exceeded (403)")
                resp.raise_for_status()
                return resp.json()
            except (httpx.HTTPError, httpx.RequestError) as e:
                last_err = e
                backoff = 2 ** attempt
                time.sleep(backoff)
        raise last_err or RuntimeError("NVD request failed")

    def search_cves(self, keyword: str, max_results: int = 20) -> list[str]:
        """Search NVD by keyword, return CVE IDs. Uses cache."""
        cache_path = self._cache_path(f"kw_{keyword}_{max_results}")
        if cache_path.exists():
            with open(cache_path) as f:
                data = json.load(f)
            return data.get("cve_ids", [])

        params = {
            "keywordSearch": keyword,
            "resultsPerPage": min(max_results, 50),
        }
        data = self._request_with_retry(NVD_BASE, params)
        vulns = data.get("vulnerabilities", [])
        cve_ids = []
        for v in vulns:
            cve_id = v.get("cve", {}).get("id")
            if cve_id and cve_id not in cve_ids:
                cve_ids.append(cve_id)
            if len(cve_ids) >= max_results:
                break

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w") as f:
            json.dump({"keyword": keyword, "cve_ids": cve_ids}, f)

        return cve_ids
