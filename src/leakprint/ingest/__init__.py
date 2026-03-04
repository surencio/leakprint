"""Ingestion modules."""

from leakprint.ingest.csv_ingest import ingest_csv
from leakprint.ingest.ha_ws_ingest import ingest_from_ha

__all__ = ["ingest_csv", "ingest_from_ha"]
