import math
from typing import Iterable


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def sort_by_distance_km(
    items: Iterable[tuple[float, float, object]],
    origin_lat: float,
    origin_lon: float,
) -> list[tuple[float, object]]:
    results: list[tuple[float, object]] = []
    for lat, lon, payload in items:
        d = haversine_km(origin_lat, origin_lon, lat, lon)
        results.append((d, payload))
    results.sort(key=lambda x: x[0])
    return results


