"""Home Assistant WebSocket ingestion."""

import asyncio
import hashlib
import json
import os

from leakprint.models import Device
from leakprint.match import normalize_vendor, normalize_model

# Category mapping from HA device class or model hints
CATEGORY_MAP = {
    "router": ["router", "gateway", "access point"],
    "camera": ["camera", "doorbell", "doorbell_camera"],
    "lock": ["lock", "garage"],
    "light": ["light", "plug", "switch"],
    "thermostat": ["thermostat", "climate"],
    "speaker": ["speaker", "media_player", "assistant"],
    "hub": ["hub", "bridge", "coordinator"],
    "sensor": ["sensor"],
    "appliance": ["appliance"],
}


def _infer_category(entry: dict) -> str:
    """Infer category from HA device entry."""
    model = (entry.get("model") or "").lower()
    manufacturer = (entry.get("manufacturer") or "").lower()
    combined = f"{manufacturer} {model}"

    for cat, keywords in CATEGORY_MAP.items():
        if any(kw in combined for kw in keywords):
            return cat
    return "other"


async def _fetch_devices_async() -> list[dict]:
    """Fetch device registry from HA WebSocket."""
    try:
        import websockets
    except ImportError:
        raise RuntimeError("websockets package required for --from-ha")

    hass_url = os.environ.get("HASS_URL", "")
    hass_token = os.environ.get("HASS_TOKEN", "")

    url = hass_url.rstrip("/")
    if not url.startswith("http"):
        url = f"http://{url}"
    ws_url = url.replace("http://", "ws://").replace("https://", "wss://")
    ws_url = f"{ws_url}/api/websocket"

    if not hass_token:
        raise ValueError("HASS_TOKEN env var required for --from-ha")

    async with websockets.connect(ws_url) as ws:
        msg = await ws.recv()
        data = json.loads(msg)
        if data.get("type") != "auth_required":
            raise RuntimeError(f"Unexpected HA response: {data.get('type')}")

        await ws.send(json.dumps({"type": "auth", "access_token": hass_token}))
        msg = await ws.recv()
        auth = json.loads(msg)
        if auth.get("type") != "auth_ok":
            raise RuntimeError(f"HA auth failed: {auth.get('message', 'unknown')}")

        await ws.send(json.dumps({"id": 1, "type": "config/device_registry/list"}))
        msg = await ws.recv()
        result = json.loads(msg)
        if "result" not in result:
            raise RuntimeError(f"HA device list failed: {result}")
        return result["result"]


def ingest_from_ha() -> list[Device]:
    """Ingest devices from Home Assistant. Raises on connection/auth errors."""
    if not os.environ.get("HASS_URL"):
        raise ValueError("HASS_URL env var required for --from-ha")

    entries = asyncio.run(_fetch_devices_async())
    devices: list[Device] = []

    for i, entry in enumerate(entries):
        manufacturer = str(entry.get("manufacturer") or entry.get("vendor") or "").strip()
        model = str(entry.get("model") or entry.get("model_id") or "").strip()
        name = str(entry.get("name_by_user") or entry.get("name") or "").strip()

        if not manufacturer and not model:
            continue

        raw_id = f"{manufacturer}|{model}|{entry.get('id', i)}"
        device_id = hashlib.sha256(raw_id.encode()).hexdigest()[:16]

        devices.append(
            Device(
                device_id=device_id,
                source="ha",
                category=_infer_category(entry),
                vendor=normalize_vendor(manufacturer or "unknown"),
                model=normalize_model(model or "unknown"),
                name=name or None,
                firmware_version=str(entry.get("sw_version") or "").strip() or None,
                cloud_required=None,
                raw={
                    "ha_id": entry.get("id"),
                    "area_id": entry.get("area_id"),
                },
            )
        )

    return devices
