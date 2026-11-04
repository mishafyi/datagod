import functools
import time

TTL = {
    "fred": 86400 * 30, "edgar": 86400, "usaspending": 3600 * 4,
    "census": 86400 * 7, "bls": 86400 * 7, "treasury": 3600,
    "fec": 86400, "congress": 86400, "fda": 3600 * 4,
    "clinicaltrials": 3600 * 4, "eia": 86400, "fema": 3600,
    "federal_register": 3600, "house_fd": 3600, "nasdaq": 60,
    "wilson": 86400 * 7, "smithsonian": 86400 * 7, "nara": 86400,
    "nsarchive": 3600,
    "worldbank": 86400, "imf": 86400, "eurostat": 86400, "ecb": 3600 * 4,
    "comtrade": 86400, "ucdp": 86400, "usgs": 300, "nws": 60,
    "eonet": 300, "wikipedia": 3600,
    "nasa_images": 86400, "internetarchive": 86400, "commons": 86400,
}

_cache: dict[str, tuple[float, object]] = {}


def clear_cache():
    _cache.clear()


def cached(ttl_seconds: int):
    def decorator(fn):
        # Module-qualified: fred.search and arxiv.search must not share entries.
        name = f"{fn.__module__}.{fn.__qualname__}"

        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            key = f"{name}:{args!r}:{sorted(kwargs.items())!r}"
            hit = _cache.get(key)
            if hit is not None and time.monotonic() - hit[0] < ttl_seconds:
                return hit[1]
            result = await fn(*args, **kwargs)
            # Never cache the error-dict: one upstream blip would stick for the TTL.
            if not (isinstance(result, dict) and result.get("error") is True):
                _cache[key] = (time.monotonic(), result)
            return result
        return wrapper
    return decorator
