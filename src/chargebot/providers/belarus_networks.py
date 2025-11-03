from __future__ import annotations

import aiohttp
from typing import Any
from bs4 import BeautifulSoup
import re


# Static data for Belarusian charging networks
# In production, this would be scraped from their websites
BELARUSIAN_STATIONS = [
    # User-added stations will be added here
    # Malanka stations (sample data)
    {
        "id": "malanka_minsk_1",
        "name": "Malanka ЭЗС ТЦ Dana Mall",
        "address": "пр-т Победителей, 9, Минск",
        "latitude": 53.9353,
        "longitude": 27.5125,
        "power_kw": 50,
        "operator": "Malanka",
        "network": "malanka"
    },
    {
        "id": "malanka_minsk_2",
        "name": "Malanka ЭЗС ТЦ Galleria Minsk",
        "address": "пр-т Победителей, 9, Минск",
        "latitude": 53.9094,
        "longitude": 27.5439,
        "power_kw": 75,
        "operator": "Malanka",
        "network": "malanka"
    },

    # A-100 stations (sample data)
    {
        "id": "a100_minsk_1",
        "name": "A-100 ЭЗС АЗС №1",
        "address": "ул. Притыцкого, 156, Минск",
        "latitude": 53.9045,
        "longitude": 27.5615,
        "power_kw": 22,
        "operator": "A-100",
        "network": "a100"
    },
    {
        "id": "a100_minsk_2",
        "name": "A-100 ЭЗС АЗС №15",
        "address": "ул. Филимонова, 11, Минск",
        "latitude": 53.8642,
        "longitude": 27.4758,
        "power_kw": 50,
        "operator": "A-100",
        "network": "a100"
    },

    # Belorusneft stations (sample data)
    {
        "id": "belorusneft_minsk_1",
        "name": "Belorusneft ЭЗС АЗС №1",
        "address": "ул. Рогачевская, 1, Минск",
        "latitude": 53.8567,
        "longitude": 27.4789,
        "power_kw": 22,
        "operator": "Белоруснефть",
        "network": "belorusneft"
    },
    {
        "id": "belorusneft_minsk_2",
        "name": "Belorusneft ЭЗС АЗС №5",
        "address": "пр-т Независимости, 54, Минск",
        "latitude": 53.9064,
        "longitude": 27.5547,
        "power_kw": 50,
        "operator": "Белоруснефть",
        "network": "belorusneft"
    },

    # Add more stations for other cities
    {
        "id": "malanka_gomel_1",
        "name": "Malanka ЭЗС Гомель",
        "address": "ул. Советская, 15, Гомель",
        "latitude": 52.4417,
        "longitude": 30.9754,
        "power_kw": 50,
        "operator": "Malanka",
        "network": "malanka"
    },
    {
        "id": "a100_gomel_1",
        "name": "A-100 ЭЗС Гомель",
        "address": "ул. Барыкина, 1, Гомель",
        "latitude": 52.4242,
        "longitude": 31.0147,
        "power_kw": 22,
        "operator": "A-100",
        "network": "a100"
    },
    # More Minsk stations
    {
        "id": "malanka_minsk_3",
        "name": "Malanka ЭЗС ТЦ Замок",
        "address": "пр-т Победителей, 65, Минск",
        "latitude": 53.9167,
        "longitude": 27.5817,
        "power_kw": 75,
        "operator": "Malanka",
        "network": "malanka"
    },
    {
        "id": "a100_minsk_3",
        "name": "A-100 ЭЗС АЗС №3",
        "address": "ул. Филимонова, 25, Минск",
        "latitude": 53.8642,
        "longitude": 27.4758,
        "power_kw": 50,
        "operator": "A-100",
        "network": "a100"
    },
    {
        "id": "belorusneft_minsk_3",
        "name": "Белоруснефть ЭЗС АЗС №10",
        "address": "ул. Тимирязева, 10, Минск",
        "latitude": 53.9064,
        "longitude": 27.5547,
        "power_kw": 22,
        "operator": "Белоруснефть",
        "network": "belorusneft"
    }
]


async def fetch_nearby(
    *,
    lat: float,
    lon: float,
    radius_km: float,
    max_results: int,
    api_key: str | None,
) -> list[dict[str, Any]]:
    """
    Return Belarusian charging stations within radius.
    Uses static data - in production would scrape from websites.
    """
    import math

    def haversine_distance(lat1, lon1, lat2, lon2):
        """Calculate distance between two points in km"""
        R = 6371  # Earth radius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    # Filter stations within radius
    nearby_stations = []
    for station in BELARUSIAN_STATIONS:
        distance = haversine_distance(lat, lon, station["latitude"], station["longitude"])
        if distance <= radius_km:
            station_with_distance = station.copy()
            station_with_distance["distance_km"] = distance
            nearby_stations.append(station_with_distance)

    # Sort by distance and limit results
    nearby_stations.sort(key=lambda x: x["distance_km"])
    return nearby_stations[:max_results]


def add_user_station(name: str, address: str, operator: str, lat: float, lon: float, power_kw: int = None) -> bool:
    """
    Add a new station submitted by user.
    Returns True if added successfully.
    """
    try:
        new_station = {
            "id": f"user_{len(BELARUSIAN_STATIONS) + 1}_{int(lat * 1000)}_{int(lon * 1000)}",
            "name": name,
            "address": address,
            "latitude": lat,
            "longitude": lon,
            "power_kw": power_kw or 22,  # Default 22kW if not specified
            "operator": operator or "Частная",
            "network": "user",
        }
        BELARUSIAN_STATIONS.append(new_station)
        return True
    except Exception as e:
        print(f"Error adding user station: {e}")
        return False


def normalize_record(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "ext_id": item.get("id", f"by_{item.get('network', 'unknown')}"),
        "name": item.get("name", "Зарядная станция"),
        "address": item.get("address", ""),
        "operator": item.get("operator", "Белорусская сеть"),
        "latitude": float(item.get("latitude", 0)),
        "longitude": float(item.get("longitude", 0)),
        "power_kw": item.get("power_kw"),
        "status": "available",
        "last_seen_utc": None,
        "raw": item,
    }


# Individual network providers for future extension
async def fetch_malanka_stations():
    """Fetch stations from Malanka network"""
    return [s for s in BELARUSIAN_STATIONS if s["network"] == "malanka"]

async def fetch_a100_stations():
    """Fetch stations from A-100 network"""
    return [s for s in BELARUSIAN_STATIONS if s["network"] == "a100"]

async def fetch_belorusneft_stations():
    """Fetch stations from Belorusneft network"""
    return [s for s in BELARUSIAN_STATIONS if s["network"] == "belorusneft"]