from __future__ import annotations

import aiohttp
from typing import Any

OCM_BASE = "https://api.openchargemap.io/v3/poi/"


async def fetch_nearby(
    *,
    lat: float,
    lon: float,
    radius_km: float,
    max_results: int,
    api_key: str | None,
) -> list[dict[str, Any]]:
    params = {
        "output": "json",
        "latitude": str(lat),
        "longitude": str(lon),
        "distance": str(radius_km),
        "distanceunit": "KM",
        "countrycode": "BY",
        "maxresults": str(max(1, min(max_results, 100))),
        "compact": "true",
        "verbose": "false",
    }
    headers = {}
    if api_key and api_key.strip():
        headers["X-API-Key"] = api_key
    async with aiohttp.ClientSession(headers=headers) as session:
        # Convert params to ensure all values are strings
        str_params = {k: str(v) for k, v in params.items()}

        async with session.get(OCM_BASE, params=str_params, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return list(data)


def normalize_record(item: dict[str, Any]) -> dict[str, Any]:
    addr_info = item.get("AddressInfo", {})
    operator_info = item.get("OperatorInfo", {})
    status_info = item.get("StatusType", {})
    connections = item.get("Connections", []) or []
    max_power = None
    try:
        max_power = max((c.get("PowerKW") or 0) for c in connections) if connections else None
    except Exception:
        max_power = None
    return {
        "ext_id": str(item.get("ID")),
        "name": addr_info.get("Title"),
        "address": addr_info.get("AddressLine1"),
        "operator": operator_info.get("Title"),
        "latitude": float(addr_info.get("Latitude")),
        "longitude": float(addr_info.get("Longitude")),
        "power_kw": max_power,
        "status": status_info.get("Title"),
        "last_seen_utc": item.get("DateLastStatusUpdate"),
        "raw": item,
    }


