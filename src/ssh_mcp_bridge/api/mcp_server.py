"""FastMCP server implementation."""

import logging
from typing import Optional

from fastmcp import FastMCP

from ssh_mcp_bridge.services.mcp_service import McpService

logger = logging.getLogger(__name__)


def create_mcp_server(service: McpService, name: str = "SSH Bridge", auth=None) -> FastMCP:
    """Create and configure FastMCP server.

    Args:
        service: MCP service instance
        name: Server name
        auth: Optional FastMCP auth provider (e.g., JWTVerifier)

    Returns:
        Configured FastMCP server
    """
    mcp = FastMCP(name, auth=auth)

    @mcp.tool()
    def list_hosts() -> list[dict]:
        """List all available SSH hosts.

        Returns a list of configured hosts with their names and descriptions.
        Does not reveal actual hostnames, IP addresses, or credentials.

        Returns:
            List of hosts with 'name' and 'description' fields
        """
        return service.list_hosts()

    @mcp.tool()
    def execute_command(host: str, command: str) -> dict:
        """Execute a command on a specific SSH host.

        Sessions are maintained, so environment variables and working directory
        changes persist across commands for the same host.

        Args:
            host: Name of the host to execute command on
            command: Command to execute

        Returns:
            Dictionary containing:
                - host: Host name
                - command: Executed command
                - output: Command output
                - success: Whether command succeeded
                - exit_status: Exit status code (if failed)
        """
        return service.execute_command(host, command)

    @mcp.tool()
    def get_working_directory(host: str) -> dict:
        """Get the current working directory for a host's session.

        Args:
            host: Name of the host

        Returns:
            Dictionary containing:
                - host: Host name
                - working_directory: Current working directory path
        """
        return service.get_working_directory(host)

    @mcp.tool()
    def close_session(host: str) -> dict:
        """Close the SSH session for a specific host.

        This will disconnect the SSH session and free up resources.
        A new session will be created on the next command execution.

        Args:
            host: Name of the host

        Returns:
            Dictionary containing:
                - host: Host name
                - message: Status message
        """
        return service.close_session(host)

    @mcp.tool()
    def get_session_stats() -> dict:
        """Get statistics about active SSH sessions.

        Returns:
            Dictionary containing session statistics:
                - total_hosts: Total number of configured hosts
                - active_host_connections: Number of hosts with active sessions
                - total_sessions: Total number of active SSH sessions
                - hosts: Per-host session information
        """
        return service.get_session_stats()

    logger.info(f"FastMCP server '{name}' created with 4 tools (list_hosts, execute_command, get_working_directory, close_session)")
    return mcp
