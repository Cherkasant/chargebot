from __future__ import annotations

import aiohttp
from typing import Any

PLUGSHARE_BASE = "https://api.plugshare.com/v3/locations/region"


async def fetch_nearby(
    *,
    lat: float,
    lon: float,
    radius_km: float,
    max_results: int,
    api_key: str | None,
) -> list[dict[str, Any]]:
    # PlugShare uses miles, convert km to miles
    radius_miles = radius_km * 0.621371

    params = {
        "latitude": lat,
        "longitude": lon,
        "distance": radius_miles,
        "count": min(max_results, 50),  # PlugShare limit
        "minimal": "false",
        "access": "public",
    }

    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(PLUGSHARE_BASE, params=params, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            if resp.status == 403:
                # PlugShare blocks requests without proper API key or from certain regions
                return []
            resp.raise_for_status()
            data = await resp.json()
            return list(data) if isinstance(data, list) else []


def normalize_record(item: dict[str, Any]) -> dict[str, Any]:
    addr_info = item.get("address", {})
    operator_info = item.get("operator", {})
    connections = item.get("stations", [{}])[0].get("outlets", []) if item.get("stations") else []

    # Calculate max power
    max_power = None
    if connections:
        powers = []
        for outlet in connections:
            if outlet.get("power"):
                powers.append(outlet["power"])
        max_power = max(powers) if powers else None

    return {
        "ext_id": f"ps_{item.get('id')}",
        "name": item.get("name"),
        "address": f"{addr_info.get('street', '')}, {addr_info.get('city', '')}".strip(", "),
        "operator": operator_info.get("name") if operator_info else None,
        "latitude": float(item.get("latitude", 0)),
        "longitude": float(item.get("longitude", 0)),
        "power_kw": max_power,
        "status": "available" if item.get("available", False) else "unknown",
        "last_seen_utc": item.get("updated_at"),
        "raw": item,
    }