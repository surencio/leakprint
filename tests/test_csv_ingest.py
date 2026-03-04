"""Tests for CSV ingestion."""

import tempfile
from pathlib import Path

import pytest

from leakprint.ingest.csv_ingest import ingest_csv, REQUIRED_COLUMNS


def test_csv_schema_validation_missing_columns():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("category,vendor\n")
        f.write("router,tp-link\n")
        path = Path(f.name)
    try:
        with pytest.raises(ValueError, match="missing required"):
            ingest_csv(path)
    finally:
        path.unlink()


def test_csv_schema_validation_invalid_category():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("category,vendor,model\n")
        f.write("invalid_cat,tp-link,Archer\n")
        path = Path(f.name)
    try:
        with pytest.raises(ValueError, match="invalid category"):
            ingest_csv(path)
    finally:
        path.unlink()


def test_csv_ingest_valid():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("category,vendor,model\n")
        f.write("router,tp-link,Archer A7\n")
        f.write("light,philips,Hue\n")
        path = Path(f.name)
    try:
        devices = ingest_csv(path)
        assert len(devices) == 2
        assert devices[0].category == "router"
        assert devices[0].vendor == "tp-link"
        assert devices[0].model == "archer a7"
        assert devices[0].device_id
    finally:
        path.unlink()
