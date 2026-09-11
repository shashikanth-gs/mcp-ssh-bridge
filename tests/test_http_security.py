"""HTTP transport authentication and safe-default tests."""

import asyncio
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

from ssh_mcp_bridge.api.http_server import create_fastmcp_auth, create_http_server
from ssh_mcp_bridge.models.config import Config, HostConfig, ServerConfig


class FakeService:
    """Minimal service used to exercise the mounted MCP and REST surfaces."""

    def __init__(self, config: Config | None = None):
        self.session_manager = SimpleNamespace(config=config or Config())

    def list_hosts(self):
        return []


def mcp_tools_list_request() -> dict:
    """Return a modern, stateless MCP tools/list request."""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {},
        "_meta": {
            "io.modelcontextprotocol/protocolVersion": "2026-07-28",
            "io.modelcontextprotocol/clientInfo": {"name": "test", "version": "1"},
            "io.modelcontextprotocol/clientCapabilities": {},
        },
    }


def test_server_defaults_to_loopback():
    assert ServerConfig().host == "127.0.0.1"


def test_api_key_uses_fastmcp_token_verifier():
    auth = create_fastmcp_auth(ServerConfig(auth_mode="api_key", api_key="test-secret"))

    assert isinstance(auth, StaticTokenVerifier)
    assert asyncio.run(auth.verify_token("test-secret")) is not None
    assert asyncio.run(auth.verify_token("wrong")) is None


def test_explicit_api_key_mode_fails_closed_without_key(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("SSH_MCP_API_KEY", raising=False)

    with pytest.raises(ValueError, match="requires api_key"):
        create_fastmcp_auth(ServerConfig(auth_mode="api_key"))


def test_non_loopback_anonymous_http_is_rejected():
    config = ServerConfig(
        host="0.0.0.0",
        auth_mode="none",
        allowed_hosts=["mcp.example.com"],
    )

    with pytest.raises(ValueError, match="Unauthenticated HTTP"):
        create_http_server(FakeService(), config)


def test_non_loopback_requires_explicit_allowed_hosts():
    config = ServerConfig(host="0.0.0.0", auth_mode="api_key", api_key="test-secret")

    with pytest.raises(ValueError, match="allowed_hosts"):
        create_http_server(FakeService(), config)


def test_http_rejects_shared_shell_sessions_by_default():
    app_config = Config(hosts=[HostConfig(name="shell-host", execution_mode="shell")])
    server_config = ServerConfig(auth_mode="api_key", api_key="test-secret")

    with pytest.raises(ValueError, match="shared shell sessions"):
        create_http_server(FakeService(app_config), server_config)


def test_mcp_endpoint_requires_configured_api_key():
    app = create_http_server(
        FakeService(),
        ServerConfig(auth_mode="api_key", api_key="test-secret"),
    )
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }

    with TestClient(app) as client:
        assert (
            client.post("/mcp", headers=headers, json=mcp_tools_list_request()).status_code == 401
        )
        assert (
            client.post(
                "/mcp",
                headers={**headers, "Authorization": "Bearer wrong"},
                json=mcp_tools_list_request(),
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/mcp",
                headers={**headers, "Authorization": "Bearer test-secret"},
                json=mcp_tools_list_request(),
            ).status_code
            == 200
        )


def test_mcp_endpoint_rejects_untrusted_browser_origin():
    app = create_http_server(
        FakeService(),
        ServerConfig(
            auth_mode="api_key",
            api_key="test-secret",
            cors_origins=["https://trusted.example"],
        ),
    )

    with TestClient(app) as client:
        response = client.post(
            "/mcp",
            headers={
                "Accept": "application/json, text/event-stream",
                "Authorization": "Bearer test-secret",
                "Content-Type": "application/json",
                "Origin": "https://evil.example",
            },
            json=mcp_tools_list_request(),
        )

    assert response.status_code == 403
