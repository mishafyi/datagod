"""Retry logic with exponential backoff for all API clients."""
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from app.clients import get_client


def _should_retry(exc: BaseException) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
        return True
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500

_retry = retry(
    retry=retry_if_exception(_should_retry),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True,
)

def _error_dict(url: str, exc: Exception) -> dict:
    status = getattr(getattr(exc, "response", None), "status_code", 0)
    return {"error": True, "source": url, "status": status, "message": str(exc)}

@_retry
async def _get(url: str, **kwargs) -> httpx.Response:
    resp = await get_client().get(url, **kwargs)
    resp.raise_for_status()
    return resp

@_retry
async def _post(url: str, **kwargs) -> httpx.Response:
    resp = await get_client().post(url, **kwargs)
    resp.raise_for_status()
    return resp

async def resilient_get(url: str, **kwargs) -> dict:
    try:
        return (await _get(url, **kwargs)).json()
    except Exception as exc:
        return _error_dict(url, exc)

async def resilient_post(url: str, data=None, json=None, **kwargs) -> dict:
    try:
        return (await _post(url, data=data, json=json, **kwargs)).json()
    except Exception as exc:
        return _error_dict(url, exc)
