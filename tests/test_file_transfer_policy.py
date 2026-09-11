"""Tests for file-transfer safety policy."""

import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from ssh_mcp_bridge.core.session_manager import SshSessionManager
from ssh_mcp_bridge.models.config import Config, HostConfig, SecurityConfig


class FakeSftp:
    """Small in-memory SFTP implementation for transfer integration tests."""

    def __init__(self):
        self.files = {"/remote/source.txt": b"hello"}
        self.directories = {"/remote", "/uploads", "/home/test"}
        self.closed = 0

    def normalize(self, path):
        if path == ".":
            return "/home/test"
        if path.startswith("/"):
            return path
        return f"/home/test/{path}".rstrip("/")

    def stat(self, path):
        if path in self.directories:
            return SimpleNamespace(st_mode=stat.S_IFDIR | 0o755, st_size=0, st_mtime=1)
        if path in self.files:
            return SimpleNamespace(
                st_mode=stat.S_IFREG | 0o640,
                st_size=len(self.files[path]),
                st_mtime=2,
            )
        raise FileNotFoundError(path)

    def listdir_attr(self, path):
        prefix = f"{path.rstrip('/')}/"
        entries = []
        for file_path, content in self.files.items():
            if file_path.startswith(prefix) and "/" not in file_path[len(prefix) :]:
                entries.append(
                    SimpleNamespace(
                        filename=file_path[len(prefix) :],
                        st_mode=stat.S_IFREG | 0o640,
                        st_size=len(content),
                        st_mtime=2,
                    )
                )
        return entries

    def get(self, remote_path, local_path):
        Path(local_path).write_bytes(self.files[remote_path])

    def put(self, local_path, remote_path):
        self.files[remote_path] = Path(local_path).read_bytes()

    def close(self):
        self.closed += 1


class FakeSftpSession:
    def __init__(self, sftp):
        self.sftp = sftp

    def open_sftp(self):
        return self.sftp


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


def test_sftp_stat_list_download_and_upload_round_trip(tmp_path, monkeypatch):
    sftp = FakeSftp()
    manager = SshSessionManager(
        Config(
            hosts=[HostConfig(name="remote")],
            security=SecurityConfig(
                allowed_local_paths=[str(tmp_path)],
                allowed_remote_write_paths=["/uploads"],
                max_file_transfer_mb=1,
            ),
        )
    )
    monkeypatch.setattr(
        manager,
        "_get_or_create_session",
        lambda host: FakeSftpSession(sftp),
    )

    metadata = manager.stat_remote_path("remote", "/remote/source.txt")
    listing = manager.list_remote_directory("remote", "/remote", limit=10)
    download_path = tmp_path / "downloaded.txt"
    downloaded = manager.download_file("remote", "/remote/source.txt", str(download_path))
    upload_path = tmp_path / "upload.txt"
    upload_path.write_bytes(b"uploaded")
    uploaded = manager.upload_file("remote", str(upload_path), "/uploads/upload.txt")

    assert metadata == {
        "host": "remote",
        "path": "/remote/source.txt",
        "type": "file",
        "size": 5,
        "mode": "0o640",
        "mtime": 2,
        "success": True,
    }
    assert listing["entries"] == [
        {
            "name": "source.txt",
            "path": "/remote/source.txt",
            "type": "file",
            "size": 5,
            "mode": "0o640",
            "mtime": 2,
        }
    ]
    assert download_path.read_bytes() == b"hello"
    assert downloaded["bytes"] == 5
    assert downloaded["sha256"] == manager._sha256_file(download_path)
    assert sftp.files["/uploads/upload.txt"] == b"uploaded"
    assert uploaded["bytes"] == 8
    assert uploaded["sha256"] == manager._sha256_file(upload_path)
    assert sftp.closed == 4


def test_sftp_transfer_refuses_implicit_overwrite(tmp_path, monkeypatch):
    sftp = FakeSftp()
    sftp.files["/uploads/existing.txt"] = b"existing"
    manager = SshSessionManager(
        Config(
            hosts=[HostConfig(name="remote")],
            security=SecurityConfig(
                allowed_local_paths=[str(tmp_path)],
                allowed_remote_write_paths=["/uploads"],
            ),
        )
    )
    monkeypatch.setattr(
        manager,
        "_get_or_create_session",
        lambda host: FakeSftpSession(sftp),
    )
    existing_download = tmp_path / "existing.txt"
    existing_download.write_bytes(b"local")

    with pytest.raises(ValueError, match="Local file already exists"):
        manager.download_file("remote", "/remote/source.txt", str(existing_download))

    with pytest.raises(ValueError, match="Remote file already exists"):
        manager.upload_file("remote", str(existing_download), "/uploads/existing.txt")
