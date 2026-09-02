"""Tests for file-transfer safety policy."""

from pathlib import Path

import pytest

from ssh_mcp_bridge.core.session_manager import SshSessionManager
from ssh_mcp_bridge.models.config import Config, SecurityConfig


def test_local_path_allowlist_allows_child_path(tmp_path):
    """Allow local paths under configured roots."""
    manager = SshSessionManager(
        Config(
            security=SecurityConfig(
                allowed_local_paths=[str(tmp_path)],
            )
        )
    )

    allowed = manager._validate_local_path(tmp_path / "nested" / "file.txt")

    assert allowed == tmp_path / "nested" / "file.txt"


def test_local_path_allowlist_rejects_outside_path(tmp_path):
    """Reject local paths outside configured roots."""
    manager = SshSessionManager(
        Config(
            security=SecurityConfig(
                allowed_local_paths=[str(tmp_path / "allowed")],
            )
        )
    )

    with pytest.raises(ValueError, match="outside allowed paths"):
        manager._validate_local_path(tmp_path / "blocked.txt")


def test_transfer_size_limit_is_enforced():
    """Reject transfers larger than the configured size limit."""
    manager = SshSessionManager(
        Config(
            security=SecurityConfig(
                max_file_transfer_mb=1,
            )
        )
    )

    with pytest.raises(ValueError, match="File is too large"):
        manager._check_transfer_size(2 * 1024 * 1024)


def test_sha256_file(tmp_path):
    """Compute local file digest for transfer results."""
    path = tmp_path / "payload.txt"
    path.write_text("hello", encoding="utf-8")
    manager = SshSessionManager(Config())

    assert (
        manager._sha256_file(Path(path)) == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e730"
        "43362938b9824"
    )
