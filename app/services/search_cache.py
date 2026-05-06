import time
import json
import hashlib
from typing import Any, Optional

TTL_SECONDS = 8 * 60  # 8 minutes (在 5-10 min 范围内)

_cache: dict[str, tuple[float, Any]] = {}

def make_key(payload: dict) -> str:
    # 让 key 稳定：排序 + hash
    s = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def get_cached(key: str) -> Optional[Any]:
    item = _cache.get(key)
    if not item:
        return None
    exp, value = item
    if time.time() > exp:
        _cache.pop(key, None)
        return None
    return value

def set_cached(key: str, value: Any) -> None:
    _cache[key] = (time.time() + TTL_SECONDS, value)
