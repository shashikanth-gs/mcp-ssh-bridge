"""Regression tests for API-key protection of the MCP endpoint."""

import asyncio

from fastapi.testclient import TestClient
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

from ssh_mcp_bridge.api.http_server import create_fastmcp_auth, create_http_server
from ssh_mcp_bridge.models.config import ServerConfig


class FakeService:
    """Minimal service for HTTP authentication tests."""

    def list_hosts(self):
        return []


def test_api_key_is_configured_as_fastmcp_authentication():
    auth = create_fastmcp_auth(ServerConfig(api_key="test-secret"))

    assert isinstance(auth, StaticTokenVerifier)
    assert asyncio.run(auth.verify_token("test-secret")) is not None
    assert asyncio.run(auth.verify_token("wrong")) is None


def test_rest_and_mcp_endpoints_both_reject_missing_or_wrong_api_key():
    app = create_http_server(FakeService(), ServerConfig(api_key="test-secret"))

    with TestClient(app) as client:
        for path in ("/api/v1/hosts", "/mcp"):
            assert client.get(path).status_code == 401
            assert client.get(path, headers={"Authorization": "Bearer wrong"}).status_code == 401

        assert (
            client.get(
                "/api/v1/hosts",
                headers={"Authorization": "Bearer test-secret"},
            ).status_code
            == 200
        )
