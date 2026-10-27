"""Small HTTP helpers with bounded responses and safe provider errors."""

from typing import Any

import httpx

TIMEOUT = httpx.Timeout(12.0, connect=5.0)
MAX_RESPONSE_BYTES = 2_000_000


async def get_json(client: httpx.AsyncClient, url: str, **kwargs: Any) -> dict[str, Any]:
    return await request_json(client, "GET", url, **kwargs)


async def post_json(client: httpx.AsyncClient, url: str, **kwargs: Any) -> dict[str, Any]:
    return await request_json(client, "POST", url, **kwargs)


async def request_json(
    client: httpx.AsyncClient, method: str, url: str, **kwargs: Any
) -> dict[str, Any]:
    try:
        response = await client.request(method, url, **kwargs)
    except httpx.TimeoutException as exc:
        raise RuntimeError("The external service timed out. Please try again.") from exc
    except httpx.RequestError as exc:
        raise RuntimeError("Could not reach the external service. Please try again.") from exc

    if len(response.content) > MAX_RESPONSE_BYTES:
        raise RuntimeError("The external service returned an oversized response.")
    if response.status_code == 401 or response.status_code == 403:
        raise RuntimeError("The external service rejected its credentials or request.")
    if response.status_code == 429:
        raise RuntimeError("The external service rate limit was reached. Please try again later.")
    if response.is_error:
        raise RuntimeError(f"The external service returned HTTP {response.status_code}.")
    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError("The external service returned invalid JSON.") from exc
    if not isinstance(data, dict):
        raise RuntimeError("The external service returned an unexpected response.")
    return data
