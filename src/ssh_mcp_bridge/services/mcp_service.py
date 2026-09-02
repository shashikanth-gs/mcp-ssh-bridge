"""MCP service layer - business logic for MCP tools."""

import logging
from typing import Any, Dict, List

from ssh_mcp_bridge.core.session_manager import SshSessionManager

logger = logging.getLogger(__name__)


class McpService:
    """Service layer for MCP tool operations."""

    def __init__(self, session_manager: SshSessionManager):
        """Initialize MCP service.

        Args:
            session_manager: SSH session manager instance
        """
        self.session_manager = session_manager

    def list_hosts(self) -> List[Dict[str, str]]:
        """List all configured SSH hosts.

        Returns:
            List of hosts with name and description
        """
        logger.debug("Listing all configured hosts")
        return self.session_manager.list_hosts()

    def execute_command(self, host: str, command: str) -> Dict[str, Any]:
        """Execute command on specified host.

        Args:
            host: Host name
            command: Command to execute

        Returns:
            Command execution result

        Raises:
            ValueError: If host not found
        """
        logger.info(f"Executing command on {host}: {command[:50]}...")
        return self.session_manager.execute_command(host, command)

    def get_working_directory(self, host: str) -> Dict[str, str]:
        """Get current working directory for host.

        Args:
            host: Host name

        Returns:
            Working directory information

        Raises:
            ValueError: If host not found
        """
        logger.debug(f"Getting working directory for {host}")
        return self.session_manager.get_working_directory(host)

    def stat_remote_path(self, host: str, remote_path: str) -> Dict[str, Any]:
        """Get metadata for a remote file or directory."""
        logger.debug(f"Getting remote path metadata for {host}: {remote_path}")
        return self.session_manager.stat_remote_path(host, remote_path)

    def list_remote_directory(
        self, host: str, remote_path: str, limit: int = 200
    ) -> Dict[str, Any]:
        """List files in a remote directory."""
        logger.debug(f"Listing remote directory for {host}: {remote_path}")
        return self.session_manager.list_remote_directory(host, remote_path, limit)

    def download_file(
        self,
        host: str,
        remote_path: str,
        local_path: str,
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        """Download one file from a remote SSH host to the MCP server filesystem."""
        logger.info(f"Downloading file from {host}: {remote_path}")
        return self.session_manager.download_file(host, remote_path, local_path, overwrite)

    def upload_file(
        self,
        host: str,
        local_path: str,
        remote_path: str,
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        """Upload one file from the MCP server filesystem to a remote SSH host."""
        logger.info(f"Uploading file to {host}: {remote_path}")
        return self.session_manager.upload_file(host, local_path, remote_path, overwrite)

    def get_file_transfer_config(self) -> Dict[str, Any]:
        """Return file-transfer limits and server-side path policy."""
        security = self.session_manager.config.security
        return {
            "mode": "server-side",
            "local_path_meaning": (
                "Paths are local to the MCP server process. In STDIO mode this is the "
                "client machine; in HTTP mode this is the remote MCP server host."
            ),
            "allowed_local_paths": security.allowed_local_paths,
            "allowed_remote_write_paths": security.allowed_remote_write_paths,
            "max_file_transfer_mb": security.max_file_transfer_mb,
        }

    def close_session(self, host: str) -> Dict[str, str]:
        """Close SSH session for host.

        Args:
            host: Host name

        Returns:
            Session closure status
        """
        logger.info(f"Closing session for {host}")
        return self.session_manager.close_session(host)

    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about active sessions.

        Returns:
            Session statistics
        """
        with self.session_manager.lock:
            stats = {
                "total_hosts": len(self.session_manager.config.hosts),
                "active_host_connections": len(self.session_manager.sessions),
                "total_sessions": sum(
                    len(sessions) for sessions in self.session_manager.sessions.values()
                ),
                "hosts": {},
            }

            for host_name, sessions in self.session_manager.sessions.items():
                stats["hosts"][host_name] = {
                    "session_count": len(sessions),
                    "connected": any(s.connected for s in sessions),
                }

            return stats
