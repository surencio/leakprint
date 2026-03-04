"""CISA KEV catalog client with file cache."""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import httpx

KEV_URL = "https://raw.githubusercontent.com/cisagov/kev-data/develop/known_exploited_vulnerabilities.json"


class KEVClient:
    """Fetch and cache CISA KEV catalog."""

    def __init__(self, cache_dir: Path, ttl_hours: int = 24):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "kev.json"
        self.meta_file = self.cache_dir / "kev_meta.json"
        self.ttl = timedelta(hours=ttl_hours)
        self._cve_set: set[str] | None = None

    def _is_expired(self) -> bool:
        if not self.meta_file.exists():
            return True
        try:
            with open(self.meta_file) as f:
                meta = json.load(f)
            ts = datetime.fromisoformat(meta.get("fetched_at", "2000-01-01"))
            return datetime.utcnow() - ts > self.ttl
        except (json.JSONDecodeError, KeyError):
            return True

    def _fetch_and_cache(self) -> set[str]:
        """Fetch KEV JSON and extract CVE IDs."""
        response = httpx.get(KEV_URL, timeout=30)
        response.raise_for_status()
        data = response.json()

        cve_ids: set[str] = set()
        vulns = data.get("vulnerabilities", [])
        for v in vulns:
            cve = v.get("cveID")
            if cve:
                cve_ids.add(cve)

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        with open(self.cache_file, "w") as f:
            json.dump(data, f, indent=0)
        with open(self.meta_file, "w") as f:
            json.dump(
                {"fetched_at": datetime.utcnow().isoformat(), "count": len(cve_ids)},
                f,
            )
        return cve_ids

    def get_cve_set(self) -> set[str]:
        """Get set of CVE IDs in KEV. Uses cache if valid."""
        if self._cve_set is not None:
            return self._cve_set

        if self.cache_file.exists() and not self._is_expired():
            with open(self.cache_file) as f:
                data = json.load(f)
            self._cve_set = {
                    v.get("cveID")
                    for v in data.get("vulnerabilities", [])
                    if v.get("cveID")
                }
            return self._cve_set

        self._cve_set = self._fetch_and_cache()
        return self._cve_set
