"""Device-to-CVE matching logic."""

from leakprint.models import Device


# Vendor aliases for normalization
VENDOR_ALIASES: dict[str, str] = {
    "tplink": "tp-link",
    "tp-link": "tp-link",
    "tplinkusa": "tp-link",
    "netgear": "netgear",
    "linksys": "linksys",
    "amazon": "amazon",
    "google": "google",
    "nest": "google",
    "ring": "ring",
    "wyze": "wyze",
    "eufy": "eufy",
    "philips": "philips",
    "philips hue": "philips",
    "hue": "philips",
    "shelly": "shelly",
    "tuya": "tuya",
    "smartthings": "samsung",
    "samsung": "samsung",
}

NOISE_WORDS = frozenset(
    {"the", "a", "an", "inc", "llc", "ltd", "corp", "corporation", "co", "and", "or"}
)


def normalize_vendor(vendor: str) -> str:
    """Normalize vendor string."""
    if not vendor or not vendor.strip():
        return "unknown"
    s = vendor.strip().lower()
    # Remove common suffixes
    for suffix in [" inc", " llc", " ltd", " corp", " corporation"]:
        if s.endswith(suffix):
            s = s[: -len(suffix)].strip()
    return VENDOR_ALIASES.get(s, s)


def normalize_model(model: str) -> str:
    """Normalize model string."""
    if not model or not str(model).strip():
        return "unknown"
    s = str(model).strip().lower()
    # Remove noise words
    words = [w for w in s.split() if w not in NOISE_WORDS]
    return " ".join(words) if words else "unknown"


def build_search_queries(device: Device) -> list[str]:
    """Build NVD keywordSearch queries for a device."""
    vendor = normalize_vendor(device.vendor)
    model = normalize_model(device.model)
    category = device.category.lower()

    queries: list[str] = []
    if vendor != "unknown" and model != "unknown":
        queries.append(f"{vendor} {model}")
    if vendor != "unknown":
        queries.append(f"{vendor} {category}")
    return queries
