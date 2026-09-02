"""SSH session pool manager."""

import hashlib
import logging
import posixpath
import stat
import threading
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

from ssh_mcp_bridge.models.config import Config
from ssh_mcp_bridge.core.ssh_session import SshSession

logger = logging.getLogger(__name__)


class SshSessionManager:
    """Manages pool of SSH sessions with cleanup."""

    def __init__(self, config: Config):
        self.config = config
        self.sessions: Dict[str, List[SshSession]] = defaultdict(list)
        self.lock = threading.RLock()
        self.cleanup_thread = None
        self.running = False

    def start(self):
        """Start session manager and cleanup thread."""
        logger.info("Starting SSH session manager")
        self.running = True

        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()

    def stop(self):
        """Stop session manager and close all sessions."""
        logger.info("Stopping SSH session manager")
        self.running = False

        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5)

        with self.lock:
            for host_sessions in self.sessions.values():
                for session in host_sessions:
                    try:
                        session.close()
                    except Exception as e:
                        logger.error(f"Error closing session: {e}")
            self.sessions.clear()

    def list_hosts(self) -> List[Dict[str, str]]:
        """List all configured hosts."""
        return [{"name": host.name, "description": host.description} for host in self.config.hosts]

    def execute_command(self, host_name: str, command: str) -> Dict[str, Any]:
        """Execute command on host."""
        host_config = self.config.get_host(host_name)
        if not host_config:
            raise ValueError(f"Host not found: {host_name}")

        session = self._get_or_create_session(host_name)
        result = session.execute_command(command)
        return result

    def get_working_directory(self, host_name: str) -> Dict[str, str]:
        """Get working directory for host."""
        host_config = self.config.get_host(host_name)
        if not host_config:
            raise ValueError(f"Host not found: {host_name}")

        session = self._get_or_create_session(host_name)
        pwd = session.get_working_directory()

        return {"host": host_name, "working_directory": pwd}

    def stat_remote_path(self, host_name: str, remote_path: str) -> Dict[str, Any]:
        """Return metadata for a remote path."""
        self._require_host(host_name)
        session = self._get_or_create_session(host_name)
        sftp = session.open_sftp()
        try:
            normalized_path = self._normalize_remote_path(sftp, remote_path)
            attrs = sftp.stat(normalized_path)
            return {
                "host": host_name,
                "path": normalized_path,
                "type": self._file_type(attrs.st_mode),
                "size": attrs.st_size,
                "mode": oct(attrs.st_mode & 0o777),
                "mtime": attrs.st_mtime,
                "success": True,
            }
        finally:
            sftp.close()

    def list_remote_directory(
        self, host_name: str, remote_path: str, limit: int = 200
    ) -> Dict[str, Any]:
        """List entries in a remote directory."""
        self._require_host(host_name)
        if limit < 1:
            raise ValueError("limit must be greater than 0")

        session = self._get_or_create_session(host_name)
        sftp = session.open_sftp()
        try:
            normalized_path = self._normalize_remote_path(sftp, remote_path)
            entries = []
            for attrs in sftp.listdir_attr(normalized_path)[:limit]:
                entries.append(
                    {
                        "name": attrs.filename,
                        "path": posixpath.join(normalized_path, attrs.filename),
                        "type": self._file_type(attrs.st_mode),
                        "size": attrs.st_size,
                        "mode": oct(attrs.st_mode & 0o777),
                        "mtime": attrs.st_mtime,
                    }
                )

            return {
                "host": host_name,
                "path": normalized_path,
                "entries": entries,
                "count": len(entries),
                "limit": limit,
                "success": True,
            }
        finally:
            sftp.close()

    def download_file(
        self,
        host_name: str,
        remote_path: str,
        local_path: str,
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        """Download one file from a remote host using SFTP."""
        self._require_host(host_name)
        local_target = self._resolve_local_target(local_path)

        session = self._get_or_create_session(host_name)
        sftp = session.open_sftp()
        try:
            normalized_remote = self._normalize_remote_path(sftp, remote_path)
            attrs = sftp.stat(normalized_remote)
            if stat.S_ISDIR(attrs.st_mode):
                raise ValueError(f"Remote path is a directory: {normalized_remote}")
            self._check_transfer_size(attrs.st_size)

            if local_target.exists() and local_target.is_dir():
                local_target = local_target / posixpath.basename(normalized_remote)
            local_target = self._validate_local_path(local_target)
            if local_target.exists() and not overwrite:
                raise ValueError(f"Local file already exists: {local_target}")

            local_target.parent.mkdir(parents=True, exist_ok=True)
            sftp.get(normalized_remote, str(local_target))
            sha256 = self._sha256_file(local_target)

            return {
                "host": host_name,
                "remote_path": normalized_remote,
                "local_path": str(local_target),
                "bytes": local_target.stat().st_size,
                "sha256": sha256,
                "success": True,
            }
        finally:
            sftp.close()

    def upload_file(
        self,
        host_name: str,
        local_path: str,
        remote_path: str,
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        """Upload one local file to a remote host using SFTP."""
        self._require_host(host_name)
        local_source = self._validate_local_path(Path(local_path).expanduser())
        if not local_source.is_file():
            raise ValueError(f"Local path is not a file: {local_source}")
        self._check_transfer_size(local_source.stat().st_size)

        session = self._get_or_create_session(host_name)
        sftp = session.open_sftp()
        try:
            normalized_remote = self._resolve_remote_upload_target(
                sftp, remote_path, local_source.name
            )
            self._validate_remote_write_path(sftp, normalized_remote)

            try:
                existing_attrs = sftp.stat(normalized_remote)
                if stat.S_ISDIR(existing_attrs.st_mode):
                    normalized_remote = posixpath.join(normalized_remote, local_source.name)
                elif not overwrite:
                    raise ValueError(f"Remote file already exists: {normalized_remote}")
            except FileNotFoundError:
                pass

            sftp.put(str(local_source), normalized_remote)
            attrs = sftp.stat(normalized_remote)

            return {
                "host": host_name,
                "local_path": str(local_source),
                "remote_path": normalized_remote,
                "bytes": attrs.st_size,
                "sha256": self._sha256_file(local_source),
                "success": True,
            }
        finally:
            sftp.close()

    def close_session(self, host_name: str) -> Dict[str, str]:
        """Close session for host."""
        with self.lock:
            if host_name in self.sessions:
                sessions = self.sessions[host_name]
                for session in sessions:
                    session.close()
                del self.sessions[host_name]
                return {"host": host_name, "message": "Session closed successfully"}
            else:
                return {"host": host_name, "message": "No active session found"}

    def _require_host(self, host_name: str):
        """Raise if host is not configured."""
        if not self.config.get_host(host_name):
            raise ValueError(f"Host not found: {host_name}")

    def _validate_local_path(self, path: Path) -> Path:
        """Validate a local path against the configured allowlist."""
        resolved_path = path.expanduser().resolve(strict=False)
        allowed_paths = [
            Path(allowed).expanduser().resolve(strict=False)
            for allowed in self.config.security.allowed_local_paths
        ]

        if not any(self._is_relative_to(resolved_path, allowed) for allowed in allowed_paths):
            allowed = ", ".join(str(path) for path in allowed_paths)
            raise ValueError(
                f"Local path is outside allowed paths: {resolved_path}. Allowed: {allowed}"
            )

        return resolved_path

    def _resolve_local_target(self, local_path: str) -> Path:
        """Resolve a local download target without requiring it to exist."""
        return Path(local_path).expanduser().resolve(strict=False)

    def _validate_remote_write_path(self, sftp, remote_path: str):
        """Validate a remote write target against the configured allowlist."""
        allowed_roots = [
            self._expand_remote_allowed_path(sftp, path)
            for path in self.config.security.allowed_remote_write_paths
        ]
        normalized_path = posixpath.normpath(remote_path)

        if not any(
            normalized_path == root or normalized_path.startswith(f"{root.rstrip('/')}/")
            for root in allowed_roots
        ):
            allowed = ", ".join(allowed_roots)
            raise ValueError(
                f"Remote path is outside allowed write paths: {normalized_path}. Allowed: {allowed}"
            )

    def _expand_remote_allowed_path(self, sftp, path: str) -> str:
        """Expand a remote allowlist path."""
        if path == "~" or path.startswith("~/"):
            home = self._normalize_remote_path(sftp, ".")
            suffix = path[2:] if path.startswith("~/") else ""
            return posixpath.normpath(posixpath.join(home, suffix))
        return posixpath.normpath(path)

    def _resolve_remote_upload_target(self, sftp, remote_path: str, fallback_name: str) -> str:
        """Resolve the final remote upload path."""
        remote_path = remote_path.strip()
        if not remote_path:
            raise ValueError("remote_path is required")

        if remote_path.endswith("/"):
            parent = self._normalize_remote_path(sftp, remote_path)
            return posixpath.join(parent, fallback_name)

        parent, filename = posixpath.split(remote_path)
        if not filename:
            filename = fallback_name

        normalized_parent = self._normalize_remote_path(sftp, parent or ".")
        return posixpath.normpath(posixpath.join(normalized_parent, filename))

    def _normalize_remote_path(self, sftp, remote_path: str) -> str:
        """Normalize a remote path through the SFTP server."""
        if not remote_path or not remote_path.strip():
            raise ValueError("remote_path is required")
        return posixpath.normpath(sftp.normalize(remote_path))

    def _check_transfer_size(self, size_bytes: int):
        """Validate file size against configured limit."""
        max_bytes = self.config.security.max_file_transfer_mb * 1024 * 1024
        if size_bytes > max_bytes:
            raise ValueError(f"File is too large: {size_bytes} bytes. Limit: {max_bytes} bytes")

    def _sha256_file(self, path: Path) -> str:
        """Compute SHA-256 for a local file."""
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _file_type(self, mode: int) -> str:
        """Return a portable file type string from an st_mode value."""
        if stat.S_ISDIR(mode):
            return "directory"
        if stat.S_ISLNK(mode):
            return "symlink"
        if stat.S_ISREG(mode):
            return "file"
        return "other"

    def _is_relative_to(self, path: Path, parent: Path) -> bool:
        """Compatibility wrapper for Path.is_relative_to."""
        try:
            path.relative_to(parent)
            return True
        except ValueError:
            return False

    def _get_or_create_session(self, host_name: str) -> SshSession:
        """Get existing session or create new one."""
        with self.lock:
            host_sessions = self.sessions.get(host_name, [])

            # Try to find a connected session
            for session in host_sessions:
                if session.connected:
                    return session

            # Check max sessions limit
            max_sessions = self.config.session.max_sessions_per_host
            if len(host_sessions) >= max_sessions:
                logger.warning(f"Max sessions reached for {host_name}, removing oldest")
                oldest = host_sessions.pop(0)
                oldest.close()

            # Create new session
            host_config = self.config.get_host(host_name)
            session = SshSession(
                host_config,
                execution_mode=host_config.execution_mode,
                disable_pager=host_config.disable_pager,
            )
            session.connect()

            host_sessions.append(session)
            self.sessions[host_name] = host_sessions

            return session

    def _cleanup_loop(self):
        """Periodic cleanup of idle sessions."""
        while self.running:
            try:
                time.sleep(60)
                self._cleanup_idle_sessions()
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    def _cleanup_idle_sessions(self):
        """Remove idle sessions."""
        timeout = self.config.session.idle_timeout

        with self.lock:
            for host_name, host_sessions in list(self.sessions.items()):
                active_sessions = []

                for session in host_sessions:
                    if session.is_idle(timeout):
                        logger.info(f"Closing idle session to {host_name}")
                        session.close()
                    else:
                        active_sessions.append(session)

                if active_sessions:
                    self.sessions[host_name] = active_sessions
                else:
                    del self.sessions[host_name]
