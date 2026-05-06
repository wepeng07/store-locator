import asyncio
import time
from typing import Optional, Tuple
import httpx

TTL_SECONDS = 30 * 24 * 3600
_cache: dict[str, Tuple[float, Tuple[float, float]]] = {}

def _get_cache(key: str) -> Optional[Tuple[float, float]]:
    item = _cache.get(key)
    if not item:
        return None
    exp, value = item
    if time.time() > exp:
        del _cache[key]
        return None
    return value

def _set_cache(key: str, lat: float, lon: float) -> None:
    _cache[key] = (time.time() + TTL_SECONDS, (lat, lon))

_TIMEOUT = httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0)
_HEADERS = {"User-Agent": "store_locator_app/1.0", "Accept": "application/json"}
_URL = "https://nominatim.openstreetmap.org/search"

async def geocode_query(query: str) -> Tuple[float, float]:
    q = (query or "").strip()
    if not q:
        raise LookupError("Empty query string")

    key = f"nominatim::{q.lower()}"
    cached = _get_cache(key)
    if cached is not None:
        return cached

    params = {"q": q, "format": "json", "limit": 1}

    last_err: Exception | None = None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_HEADERS) as client:
                r = await client.get(_URL, params=params)
                r.raise_for_status()
                data = r.json()

            if not data:
                raise LookupError(f"Geocoding not found for: {q}")

            lat = float(data[0]["lat"])
            lon = float(data[0]["lon"])
            _set_cache(key, lat, lon)
            return lat, lon

        except (httpx.ReadTimeout, httpx.ConnectTimeout) as e:
            last_err = e
            await asyncio.sleep(0.3 * (2 ** attempt))  # 0.3, 0.6, 1.2
        except httpx.HTTPStatusError as e:
            raise Exception(f"Nominatim HTTP error: {e.response.status_code}") from e
        except httpx.HTTPError as e:
            raise Exception(f"Nominatim network error: {repr(e)}") from e

    raise Exception(f"Nominatim timeout after retries: {repr(last_err)}")