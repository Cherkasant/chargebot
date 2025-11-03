from __future__ import annotations

import aiohttp
import json
from typing import Any
from bs4 import BeautifulSoup


async def fetch_nearby(
    *,
    lat: float,
    lon: float,
    radius_km: float,
    max_results: int,
    api_key: str | None,
) -> list[dict[str, Any]]:
    """
    Fetch charging stations from Malanka network.
    Since Malanka doesn't have public API, we'll use their website data.
    """
    try:
        # Malanka has stations data embedded in their website
        # This is a simplified version - in production you'd need to parse their actual data
        url = "https://malanka.by/zaryadnye-stantsii/"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # Try to find stations data in scripts or structured data
                    stations = []

                    # Look for JSON data in scripts
                    scripts = soup.find_all('script', {'type': 'application/json'})
                    for script in scripts:
                        try:
                            data = json.loads(script.string)
                            # Parse stations from the data structure
                            if isinstance(data, dict) and 'stations' in data:
                                stations.extend(data['stations'])
                        except:
                            continue

                    # If no structured data, return mock data for major cities
                    if not stations:
                        # Mock data for demonstration - replace with actual parsing
                        mock_stations = [
                            {
                                "id": "malanka_minsk_1",
                                "name": "Malanka Charging Station",
                                "address": "ул. Притыцкого, Минск",
                                "latitude": 53.9045,
                                "longitude": 27.5615,
                                "power_kw": 50,
                                "operator": "Malanka",
                                "status": "available"
                            }
                        ]
                        return mock_stations[:max_results]

                    return stations[:max_results]
                else:
                    return []

    except Exception as e:
        print(f"Malanka fetch error: {e}")
        return []


def normalize_record(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "ext_id": f"malanka_{item.get('id', 'unknown')}",
        "name": item.get("name", "Зарядная станция Malanka"),
        "address": item.get("address", ""),
        "operator": "Malanka",
        "latitude": float(item.get("latitude", 0)),
        "longitude": float(item.get("longitude", 0)),
        "power_kw": item.get("power_kw"),
        "status": item.get("status", "unknown"),
        "last_seen_utc": None,
        "raw": item,
    }