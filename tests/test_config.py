"""Tests for configuration loading."""

import tempfile
from pathlib import Path

import pytest

from ssh_mcp_bridge.models.config import (
    HostConfig,
    OAuthConfig,
    SecurityConfig,
    ServerConfig,
    SessionConfig,
    load_config,
)


def test_host_config_creation():
    """Test creating a host configuration."""
    host = HostConfig(
        name="test-host",
        description="Test server",
        host="example.com",
        username="testuser",
        private_key_path="~/.ssh/id_rsa",
    )
    assert host.name == "test-host"
    assert host.description == "Test server"
    assert host.port == 22
    assert host.execution_mode == "exec"


def test_session_config_defaults():
    """Test session configuration defaults."""
    session = SessionConfig()
    assert session.idle_timeout == 30
    assert session.max_sessions_per_host == 5


def test_load_config():
    """Test loading configuration from YAML."""
    config_yaml = """
hosts:
  - name: server1
    description: "Test server 1"
    host: "example1.com"
    username: "user1"
    private_key_path: "~/.ssh/id_rsa"
    execution_mode: "shell"
  - name: server2
    description: "Test server 2"
    host: "example2.com"
    username: "user2"
    password: "secret"

session:
  idle_timeout: 60
  max_sessions_per_host: 10

security:
  allowed_local_paths:
    - "/tmp"
  allowed_remote_write_paths:
    - "~"
    - "/tmp"
  max_file_transfer_mb: 50
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(config_yaml)
        config_path = Path(f.name)

    try:
        config = load_config(config_path)

        assert len(config.hosts) == 2
        assert config.hosts[0].name == "server1"
        assert config.hosts[0].execution_mode == "shell"
        assert config.hosts[1].name == "server2"

        assert config.session.idle_timeout == 60
        assert config.session.max_sessions_per_host == 10
        assert config.security.allowed_local_paths == ["/tmp"]
        assert config.security.allowed_remote_write_paths == ["~", "/tmp"]
        assert config.security.max_file_transfer_mb == 50

        # Test get_host
        host = config.get_host("server1")
        assert host is not None
        assert host.name == "server1"

        host = config.get_host("nonexistent")
        assert host is None

    finally:
        config_path.unlink()


def test_load_config_file_not_found():
    """Test loading configuration from non-existent file."""
    with pytest.raises(FileNotFoundError):
        load_config(Path("/nonexistent/config.yaml"))


def test_security_config_defaults():
    """Test file-transfer security defaults."""
    security = SecurityConfig()
    assert security.allowed_local_paths == ["/tmp"]
    assert security.allowed_remote_write_paths == ["~", "/tmp"]
    assert security.max_file_transfer_mb == 100


def test_security_config_rejects_invalid_size_limit():
    """Test file-transfer size limit validation."""
    with pytest.raises(ValueError, match="max_file_transfer_mb"):
        SecurityConfig(max_file_transfer_mb=0)


def test_server_config_reads_auth_environment_and_legacy_alias(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "oauth")
    monkeypatch.setenv("SSH_MCP_API_KEY", "environment-key")
    monkeypatch.delenv("API_KEY", raising=False)

    server = ServerConfig()

    assert server.auth_mode == "oidc"
    assert server.api_key == "environment-key"
    assert server.oauth.enabled is True


@pytest.mark.parametrize("auth_mode", ["basic", "jwt", "disabled"])
def test_server_config_rejects_unknown_auth_mode(monkeypatch, auth_mode):
    monkeypatch.delenv("AUTH_MODE", raising=False)

    with pytest.raises(ValueError, match="auth_mode"):
        ServerConfig(auth_mode=auth_mode)


def test_server_config_rejects_invalid_rate_limit(monkeypatch):
    monkeypatch.delenv("AUTH_MODE", raising=False)

    with pytest.raises(ValueError, match="rate_limit_per_minute"):
        ServerConfig(rate_limit_per_minute=0)


def test_oauth_config_rejects_unknown_provider():
    with pytest.raises(ValueError, match="oauth.provider"):
        OAuthConfig(provider="custom")


def test_load_config_parses_http_security_and_oauth_fields(tmp_path, monkeypatch):
    monkeypatch.delenv("AUTH_MODE", raising=False)
    config_path = tmp_path / "config.yaml"
    config_path.write_text("""
server:
  host: 0.0.0.0
  enable_http: true
  enable_stdio: false
  auth_mode: oidc
  allowed_hosts: [mcp.example.com]
  cors_origins: [https://trusted.example]
  rate_limit_per_minute: 25
  oauth:
    enabled: true
    provider: jwt
    issuer: https://identity.example/
    audience: ssh-api
    jwks_uri: https://identity.example/jwks
    base_url: https://mcp.example.com
    required_scopes: [mcp:execute]
hosts: []
""")

    config = load_config(config_path)

    assert config.server.host == "0.0.0.0"
    assert config.server.auth_mode == "oidc"
    assert config.server.allowed_hosts == ["mcp.example.com"]
    assert config.server.cors_origins == ["https://trusted.example"]
    assert config.server.rate_limit_per_minute == 25
    assert config.server.oauth == OAuthConfig(
        enabled=True,
        provider="jwt",
        issuer="https://identity.example/",
        audience="ssh-api",
        jwks_uri="https://identity.example/jwks",
        base_url="https://mcp.example.com",
        required_scopes=["mcp:execute"],
    )
