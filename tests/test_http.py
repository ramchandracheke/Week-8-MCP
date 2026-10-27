import httpx
import pytest

from useful_mcp.http import get_json


@pytest.mark.asyncio
async def test_http_helper_parses_mocked_response():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"ok": True}))
    async with httpx.AsyncClient(transport=transport) as client:
        assert await get_json(client, "https://example.test") == {"ok": True}


@pytest.mark.asyncio
async def test_http_helper_reports_rate_limit_without_body():
    transport = httpx.MockTransport(lambda request: httpx.Response(429, text="secret internal details"))
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(RuntimeError, match="rate limit") as error:
            await get_json(client, "https://example.test")
    assert "secret" not in str(error.value)


@pytest.mark.asyncio
async def test_http_helper_reports_timeout():
    def timeout(request):
        raise httpx.ReadTimeout("timeout", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(timeout)) as client:
        with pytest.raises(RuntimeError, match="timed out"):
            await get_json(client, "https://example.test")
