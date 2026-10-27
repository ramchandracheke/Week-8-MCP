from types import SimpleNamespace

import httpx
import pytest

from useful_mcp import chatbot
from useful_mcp.server import mcp
from fastmcp import Client


@pytest.mark.asyncio
async def test_login_requires_csrf_and_authenticates(monkeypatch):
    monkeypatch.setattr(chatbot, "CHATBOT_USERNAME", "test-user")
    monkeypatch.setattr(chatbot, "CHATBOT_PASSWORD", "correct-horse-battery-staple")
    transport = httpx.ASGITransport(app=chatbot.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        session = await client.get("/api/session")
        token = session.json()["csrf_token"]
        denied = await client.post("/api/login", json={"username": "test-user", "password": "correct-horse-battery-staple"})
        assert denied.status_code == 403
        logged_in = await client.post("/api/login", json={"username": "test-user", "password": "correct-horse-battery-staple"}, headers={"X-CSRF-Token": token})
        assert logged_in.status_code == 200
        assert logged_in.json()["authenticated"] is True
        assert "useful_chat_session" in client.cookies


@pytest.mark.asyncio
async def test_chat_requires_login(monkeypatch):
    monkeypatch.setattr(chatbot, "OPENAI_API_KEY", "")
    transport = httpx.ASGITransport(app=chatbot.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        session = await client.get("/api/session")
        response = await client.post("/api/chat", json={"messages": [{"role": "user", "content": "Hi"}]},
                                     headers={"X-CSRF-Token": session.json()["csrf_token"]})
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_chat_requires_openai_key_after_login(monkeypatch):
    monkeypatch.setattr(chatbot, "CHATBOT_USERNAME", "test-user")
    monkeypatch.setattr(chatbot, "CHATBOT_PASSWORD", "test-password")
    monkeypatch.setattr(chatbot, "OPENAI_API_KEY", "")
    transport = httpx.ASGITransport(app=chatbot.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        session = await client.get("/api/session")
        login = await client.post("/api/login", json={"username": "test-user", "password": "test-password"},
                                  headers={"X-CSRF-Token": session.json()["csrf_token"]})
        response = await client.post("/api/chat", json={"messages": [{"role": "user", "content": "Hi"}]},
                                     headers={"X-CSRF-Token": login.json()["csrf_token"]})
        assert response.status_code == 503
        assert "OPENAI_API_KEY" in response.json()["detail"]


@pytest.mark.asyncio
async def test_tool_call_loop_uses_mcp_client():
    call = SimpleNamespace(type="function_call", name="service_status", arguments="{}", call_id="call_1")
    final = SimpleNamespace(type="message")

    class FakeResponses:
        def __init__(self):
            self.calls = 0

        async def create(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                assert any(tool["name"] == "get_current_weather" for tool in kwargs["tools"])
                return SimpleNamespace(output=[call], output_text="")
            assert any(isinstance(item, dict) and item.get("type") == "function_call_output" for item in kwargs["input"])
            return SimpleNamespace(output=[final], output_text="The weather tools are ready.")

    fake_model = SimpleNamespace(responses=FakeResponses())
    async with Client(mcp) as mcp_client:
        answer = await chatbot._run_chat(fake_model, mcp_client, [chatbot.ChatMessage(role="user", content="What can you do?")])
    assert answer == "The weather tools are ready."
