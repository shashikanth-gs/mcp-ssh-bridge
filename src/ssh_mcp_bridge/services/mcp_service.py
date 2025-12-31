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
