"""HTTP transport authentication and safe-default tests."""

import asyncio
import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from fastmcp.server.auth import MultiAuth, RemoteAuthProvider
from fastmcp.server.auth.providers.jwt import JWTVerifier, StaticTokenVerifier

from ssh_mcp_bridge.api.http_server import create_fastmcp_auth, create_http_server
from ssh_mcp_bridge.models.config import Config, HostConfig, OAuthConfig, ServerConfig
from ssh_mcp_bridge.models.results import CommandResult


class FakeService:
    """Minimal service used to exercise the mounted MCP and REST surfaces."""

    def __init__(self, config: Config | None = None):
        self.session_manager = SimpleNamespace(config=config or Config())

    def list_hosts(self):
        return []

    def execute_command(self, host, command):
        return CommandResult(host=host, output="done", success=True, exit_status=0)

    def get_working_directory(self, host):
        return {"host": host, "working_directory": "/srv/app"}

    def get_file_transfer_config(self):
        return {"mode": "server-side"}

    def stat_remote_path(self, host, remote_path):
        return {"host": host, "path": remote_path, "type": "file", "success": True}

    def list_remote_directory(self, host, remote_path, limit):
        return {"host": host, "path": remote_path, "entries": [], "limit": limit}

    def download_file(self, host, remote_path, local_path, overwrite):
        return {"host": host, "remote_path": remote_path, "local_path": local_path}

    def upload_file(self, host, local_path, remote_path, overwrite):
        return {"host": host, "local_path": local_path, "remote_path": remote_path}

    def close_session(self, host):
        return {"host": host, "message": "closed"}

    def get_session_stats(self):
        return {"total_sessions": 0}


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


def mcp_headers(token: str = "test-secret", **extra) -> dict:
    """Return headers for a Streamable HTTP MCP request."""
    return {
        "Accept": "application/json, text/event-stream",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        **extra,
    }


def test_server_defaults_to_loopback(monkeypatch):
    monkeypatch.delenv("AUTH_MODE", raising=False)
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("SSH_MCP_API_KEY", raising=False)
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


@pytest.mark.parametrize(
    ("oauth", "message"),
    [
        (
            OAuthConfig(
                enabled=True,
                provider="jwt",
                audience="api",
                jwks_uri="https://idp/jwks",
                base_url="https://mcp.example.com",
            ),
            "issuer and audience",
        ),
        (
            OAuthConfig(
                enabled=True,
                provider="jwt",
                issuer="https://idp",
                audience="api",
                base_url="https://mcp.example.com",
            ),
            "requires jwks_uri",
        ),
        (
            OAuthConfig(
                enabled=True,
                provider="jwt",
                issuer="https://idp",
                audience="api",
                jwks_uri="https://idp/jwks",
            ),
            "requires oauth.base_url",
        ),
    ],
)
def test_explicit_oidc_mode_fails_closed_for_incomplete_config(oauth, message):
    with pytest.raises(ValueError, match=message):
        create_fastmcp_auth(ServerConfig(auth_mode="oidc", oauth=oauth))


def test_jwt_verifier_checks_signature_issuer_audience_and_scope():
    auth = create_fastmcp_auth(
        ServerConfig(
            auth_mode="oidc",
            oauth=OAuthConfig(
                enabled=True,
                provider="jwt",
                issuer="https://identity.example/",
                audience="ssh-api",
                jwks_uri="https://identity.example/jwks",
                base_url="https://mcp.example.com",
                required_scopes=["mcp:execute"],
            ),
        )
    )
    assert isinstance(auth, RemoteAuthProvider)
    verifier = auth.token_verifier
    assert isinstance(verifier, JWTVerifier)

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    async def verification_key(_token):
        return public_key

    verifier._get_verification_key = verification_key
    claims = {
        "iss": "https://identity.example",
        "aud": "ssh-api",
        "sub": "client-1",
        "scope": "mcp:execute",
        "exp": int(time.time()) + 300,
    }
    valid_token = jwt.encode(claims, private_key, algorithm="RS256")
    wrong_audience_token = jwt.encode(
        {**claims, "aud": "other-api"}, private_key, algorithm="RS256"
    )
    wrong_issuer_token = jwt.encode(
        {**claims, "iss": "https://other.example"}, private_key, algorithm="RS256"
    )
    missing_scope_token = jwt.encode(
        {**claims, "scope": "mcp:read"}, private_key, algorithm="RS256"
    )
    expired_token = jwt.encode(
        {**claims, "exp": int(time.time()) - 1}, private_key, algorithm="RS256"
    )
    other_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    bad_signature_token = jwt.encode(claims, other_private_key, algorithm="RS256")

    access_token = asyncio.run(auth.verify_token(valid_token))
    assert access_token is not None
    assert access_token.client_id == "client-1"
    assert asyncio.run(auth.verify_token(wrong_audience_token)) is None
    assert asyncio.run(auth.verify_token(wrong_issuer_token)) is None
    assert asyncio.run(auth.verify_token(missing_scope_token)) is None
    assert asyncio.run(auth.verify_token(expired_token)) is None
    assert asyncio.run(auth.verify_token(bad_signature_token)) is None


def test_jwt_mode_publishes_rfc9728_protected_resource_metadata():
    app = create_http_server(
        FakeService(),
        ServerConfig(
            auth_mode="oidc",
            oauth=OAuthConfig(
                enabled=True,
                provider="jwt",
                issuer="https://identity.example/",
                audience="ssh-api",
                jwks_uri="https://identity.example/jwks",
                base_url="https://mcp.example.com",
                required_scopes=["mcp:execute"],
            ),
        ),
    )

    with TestClient(app, base_url="https://mcp.example.com") as client:
        challenge = client.post(
            "/mcp",
            headers={
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
            },
            json=mcp_tools_list_request(),
        )
        metadata = client.get("/.well-known/oauth-protected-resource/mcp")

    assert challenge.status_code == 401
    challenge_header = challenge.headers["www-authenticate"]
    assert challenge_header.startswith("Bearer ")
    assert 'scope="mcp:execute"' in challenge_header
    assert (
        'resource_metadata="https://mcp.example.com/.well-known/oauth-protected-resource/mcp"'
        in challenge_header
    )
    assert metadata.status_code == 200
    assert metadata.json() == {
        "resource": "https://mcp.example.com/mcp",
        "authorization_servers": ["https://identity.example/"],
        "scopes_supported": ["mcp:execute"],
        "bearer_methods_supported": ["header"],
        "resource_name": "SSH MCP Bridge",
    }


def test_auto_mode_combines_api_key_and_jwt_verifiers():
    auth = create_fastmcp_auth(
        ServerConfig(
            auth_mode="auto",
            api_key="test-secret",
            oauth=OAuthConfig(
                enabled=True,
                provider="jwt",
                issuer="https://identity.example",
                audience="ssh-api",
                jwks_uri="https://identity.example/jwks",
                base_url="https://mcp.example.com",
            ),
        )
    )

    assert isinstance(auth, MultiAuth)
    assert isinstance(auth.server, RemoteAuthProvider)
    assert isinstance(auth.server.token_verifier, JWTVerifier)
    assert [type(verifier) for verifier in auth.verifiers] == [StaticTokenVerifier]
    assert asyncio.run(auth.verify_token("test-secret")) is not None


def test_auth0_provider_uses_framework_configuration(monkeypatch):
    import fastmcp.server.auth.providers.auth0 as auth0_module

    captured = {}

    class FakeAuth0Provider:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(auth0_module, "Auth0Provider", FakeAuth0Provider)
    monkeypatch.setenv("AUTH0_CLIENT_ID", "client-id")
    monkeypatch.setenv("AUTH0_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("JWT_SIGNING_KEY", "stable-signing-key")

    auth = create_fastmcp_auth(
        ServerConfig(
            auth_mode="oidc",
            oauth=OAuthConfig(
                enabled=True,
                provider="auth0",
                issuer="https://tenant.auth0.com/",
                audience="ssh-api",
                base_url="https://mcp.example.com",
                required_scopes=["mcp:execute"],
            ),
        )
    )

    assert isinstance(auth, FakeAuth0Provider)
    assert captured == {
        "config_url": "https://tenant.auth0.com/.well-known/openid-configuration",
        "client_id": "client-id",
        "client_secret": "client-secret",
        "audience": "ssh-api",
        "base_url": "https://mcp.example.com",
        "required_scopes": ["mcp:execute"],
        "jwt_signing_key": "stable-signing-key",
    }


def test_auth0_provider_fails_closed_without_client_credentials(monkeypatch):
    monkeypatch.delenv("AUTH0_CLIENT_ID", raising=False)
    monkeypatch.delenv("AUTH0_CLIENT_SECRET", raising=False)

    with pytest.raises(ValueError, match="AUTH0_CLIENT_ID"):
        create_fastmcp_auth(
            ServerConfig(
                auth_mode="oidc",
                oauth=OAuthConfig(
                    enabled=True,
                    provider="auth0",
                    issuer="https://tenant.auth0.com",
                    audience="ssh-api",
                    base_url="https://mcp.example.com",
                ),
            )
        )


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


def test_remote_wildcard_host_and_origin_are_rejected():
    with pytest.raises(ValueError, match="allowed_hosts"):
        create_http_server(
            FakeService(),
            ServerConfig(
                host="0.0.0.0",
                auth_mode="api_key",
                api_key="test-secret",
                allowed_hosts=["*"],
            ),
        )


def test_anonymous_http_is_local_unless_remote_risk_is_explicitly_accepted():
    local_app = create_http_server(FakeService(), ServerConfig(auth_mode="none"))
    remote_app = create_http_server(
        FakeService(),
        ServerConfig(
            host="0.0.0.0",
            auth_mode="none",
            allowed_hosts=["mcp.example.com"],
            allow_unauthenticated_http=True,
        ),
    )

    assert local_app is not None
    assert remote_app is not None

    with pytest.raises(ValueError, match="cors_origins"):
        create_http_server(
            FakeService(),
            ServerConfig(
                host="0.0.0.0",
                auth_mode="api_key",
                api_key="test-secret",
                allowed_hosts=["mcp.example.com"],
                cors_origins=["*"],
            ),
        )


def test_http_rejects_shared_shell_sessions_by_default():
    app_config = Config(hosts=[HostConfig(name="shell-host", execution_mode="shell")])
    server_config = ServerConfig(auth_mode="api_key", api_key="test-secret")

    with pytest.raises(ValueError, match="shared shell sessions"):
        create_http_server(FakeService(app_config), server_config)


def test_explicit_single_principal_shell_opt_in_is_accepted():
    app_config = Config(hosts=[HostConfig(name="shell-host", execution_mode="shell")])

    app = create_http_server(
        FakeService(app_config),
        ServerConfig(
            auth_mode="api_key",
            api_key="test-secret",
            allow_shared_shell_sessions=True,
        ),
    )

    assert app is not None


def test_mcp_endpoint_requires_configured_api_key():
    app = create_http_server(
        FakeService(),
        ServerConfig(auth_mode="api_key", api_key="test-secret"),
    )
    headers = mcp_headers()

    with TestClient(app) as client:
        assert (
            client.post(
                "/mcp",
                headers={key: value for key, value in headers.items() if key != "Authorization"},
                json=mcp_tools_list_request(),
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/mcp",
                headers=mcp_headers("wrong"),
                json=mcp_tools_list_request(),
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/mcp",
                headers=headers,
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
            headers=mcp_headers(Origin="https://evil.example"),
            json=mcp_tools_list_request(),
        )

    assert response.status_code == 403


def test_mcp_endpoint_rejects_untrusted_host_and_accepts_trusted_origin():
    app = create_http_server(
        FakeService(),
        ServerConfig(
            host="0.0.0.0",
            auth_mode="api_key",
            api_key="test-secret",
            allowed_hosts=["mcp.example.com"],
            cors_origins=["https://trusted.example"],
        ),
    )

    with TestClient(app, base_url="https://mcp.example.com") as client:
        rejected = client.post(
            "/mcp",
            headers=mcp_headers(Host="evil.example"),
            json=mcp_tools_list_request(),
        )
        accepted = client.post(
            "/mcp",
            headers=mcp_headers(Origin="https://trusted.example"),
            json=mcp_tools_list_request(),
        )

    assert rejected.status_code == 421
    assert accepted.status_code == 200


def test_rate_limit_is_applied_per_authenticated_client():
    app = create_http_server(
        FakeService(),
        ServerConfig(
            auth_mode="api_key",
            api_key="test-secret",
            rate_limit_per_minute=1,
        ),
    )

    with TestClient(app) as client:
        first = client.post("/mcp", headers=mcp_headers(), json=mcp_tools_list_request())
        second_request = mcp_tools_list_request()
        second_request["id"] = 2
        second = client.post("/mcp", headers=mcp_headers(), json=second_request)

    assert first.status_code == 200
    assert "Rate limit exceeded" in second.text
    assert "configured-api-key" in second.text


def test_mcp_masks_unexpected_tool_error_details_from_client():
    class FailingService(FakeService):
        def execute_command(self, host, command):
            raise RuntimeError("sensitive-backend-error")

    app = create_http_server(
        FailingService(),
        ServerConfig(auth_mode="api_key", api_key="test-secret"),
    )
    request = mcp_tools_list_request()
    request.update(
        {
            "method": "tools/call",
            "params": {
                "name": "execute_command",
                "arguments": {"host": "test-host", "command": "secret-command"},
            },
        }
    )

    with TestClient(app) as client:
        response = client.post("/mcp", headers=mcp_headers(), json=request)

    assert response.status_code == 200
    assert "Error calling tool" in response.text
    assert "sensitive-backend-error" not in response.text
    assert "secret-command" not in response.text


def test_rest_masks_unexpected_error_details_from_client_and_logs(caplog):
    class FailingService(FakeService):
        def execute_command(self, host, command):
            raise RuntimeError("sensitive-backend-error")

    app = create_http_server(
        FailingService(),
        ServerConfig(auth_mode="api_key", api_key="test-secret"),
    )

    with caplog.at_level("ERROR"), TestClient(app) as client:
        response = client.post(
            "/api/v1/execute",
            headers={"Authorization": "Bearer test-secret"},
            json={"host": "test-host", "command": "secret-command"},
        )

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "RuntimeError" in caplog.text
    assert "sensitive-backend-error" not in caplog.text
    assert "secret-command" not in caplog.text


def test_rest_compatibility_routes_share_auth_and_serialize_results():
    app = create_http_server(
        FakeService(),
        ServerConfig(auth_mode="api_key", api_key="test-secret"),
    )
    auth = {"Authorization": "Bearer test-secret"}

    with TestClient(app) as client:
        assert client.get("/api/v1/hosts", headers=auth).json() == []
        command = client.post(
            "/api/v1/execute",
            headers=auth,
            json={"host": "test-host", "command": "secret-command"},
        ).json()
        assert command == {
            "host": "test-host",
            "output": "done",
            "success": True,
            "exit_status": 0,
        }
        assert (
            client.post(
                "/api/v1/working-directory",
                headers=auth,
                json={"host": "test-host"},
            ).status_code
            == 200
        )
        assert client.get("/api/v1/file-transfer-config", headers=auth).status_code == 200
        assert (
            client.post(
                "/api/v1/remote/stat",
                headers=auth,
                json={"host": "test-host", "remote_path": "/tmp/file"},
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/api/v1/remote/list",
                headers=auth,
                json={"host": "test-host", "remote_path": "/tmp", "limit": 10},
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/api/v1/download",
                headers=auth,
                json={
                    "host": "test-host",
                    "remote_path": "/tmp/file",
                    "local_path": "/tmp/file",
                },
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/api/v1/upload",
                headers=auth,
                json={
                    "host": "test-host",
                    "local_path": "/tmp/file",
                    "remote_path": "/tmp/file",
                },
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/api/v1/close-session",
                headers=auth,
                json={"host": "test-host"},
            ).status_code
            == 200
        )
        assert client.get("/api/v1/stats", headers=auth).status_code == 200
