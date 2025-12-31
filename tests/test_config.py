"""Tests for configuration loading."""

import tempfile
from pathlib import Path

import pytest

from ssh_mcp_bridge.config import HostConfig, SessionConfig, load_config


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
