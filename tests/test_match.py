"""Tests for vendor/model normalization."""

import pytest

from leakprint.match import normalize_vendor, normalize_model, build_search_queries
from leakprint.models import Device


def test_normalize_vendor_unknown():
    assert normalize_vendor("") == "unknown"
    assert normalize_vendor("   ") == "unknown"


def test_normalize_vendor_aliases():
    assert normalize_vendor("tplink") == "tp-link"
    assert normalize_vendor("TP-Link") == "tp-link"
    assert normalize_vendor("Nest") == "google"


def test_normalize_vendor_strips_suffix():
    assert "inc" not in normalize_vendor("Acme Inc").lower()
    assert "llc" not in normalize_vendor("Foo LLC").lower()


def test_normalize_model_unknown():
    assert normalize_model("") == "unknown"
    assert normalize_model("   ") == "unknown"


def test_normalize_model_removes_noise():
    result = normalize_model("Model X Inc")
    assert "inc" not in result.split()


def test_build_search_queries():
    device = Device(
        device_id="x",
        source="csv",
        category="router",
        vendor="tp-link",
        model="Archer A7",
    )
    queries = build_search_queries(device)
    assert any("tp-link" in q for q in queries)
    assert any("archer" in q or "a7" in q for q in queries)
    assert any("router" in q for q in queries)
