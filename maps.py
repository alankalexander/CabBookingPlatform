import math
import googlemaps
from .config import settings

def _haversine_m(lat1, lng1, lat2, lng2):
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lng2 - lng1) / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(a))

def distance_time(o: tuple, d: tuple) -> tuple[int, int]:
    """(meters, seconds). Google Distance Matrix if a key is set, else straight-line estimate."""
    if settings.google_maps_key:
        try:
            gm = googlemaps.Client(key=settings.google_maps_key)
            el = gm.distance_matrix([o], [d], mode="driving")["rows"][0]["elements"][0]
            if el["status"] == "OK":
                return el["distance"]["value"], el["duration"]["value"]
        except Exception:
            pass
    meters = int(_haversine_m(*o, *d) * 1.3)
    return meters, int(meters / (30000 / 3600))   # ~30 km/h

import math

# Fixed price per distance range (INR). Edit these numbers to change prices.
# (up to this many km, price)
FARE_SLABS = [
    (1, 40),
    (2, 60),
    (3, 80),
    (5, 120),
    (8, 180),
    (12, 260),
    (20, 400),
]
EXTRA_PER_KM = 18      # for every extra km (rounded up) beyond the last slab

def calc_fare(meters: int, secs: int = 0) -> float:
    """Slab pricing: the fare depends only on which km range the trip falls in."""
    km = meters / 1000
    for limit, price in FARE_SLABS:
        if km <= limit:
            return float(price)
    last_limit, last_price = FARE_SLABS[-1]
    return float(last_price + math.ceil(km - last_limit) * EXTRA_PER_KM)