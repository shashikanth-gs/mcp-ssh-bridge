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
    def get_file_transfer_config() -> dict:
        """Get file-transfer limits and path policy.

        File transfers are server-side. In STDIO mode, local paths are on the
        same machine running Codex/Claude. In HTTP mode, local paths are on the
        remote MCP server host, not on the connecting laptop.

        Returns:
            Dictionary containing:
                - mode: Transfer mode
                - local_path_meaning: Explanation of local path semantics
                - allowed_local_paths: Server-local paths allowed for transfer
                - allowed_remote_write_paths: Remote paths allowed for upload
                - max_file_transfer_mb: Maximum file size for upload/download
        """
        return service.get_file_transfer_config()

    @mcp.tool()
    def stat_remote_path(host: str, remote_path: str) -> dict:
        """Get metadata for a file or directory on a remote SSH host.

        Args:
            host: Name of the host
            remote_path: Path on the remote SSH host

        Returns:
            Dictionary containing path, type, size, mode, mtime, and success.
        """
        return service.stat_remote_path(host, remote_path)

    @mcp.tool()
    def list_remote_directory(host: str, remote_path: str, limit: int = 200) -> dict:
        """List a directory on a remote SSH host.

        Args:
            host: Name of the host
            remote_path: Directory path on the remote SSH host
            limit: Maximum entries to return

        Returns:
            Dictionary containing directory entries and count.
        """
        return service.list_remote_directory(host, remote_path, limit)

    @mcp.tool()
    def download_file(
        host: str,
        remote_path: str,
        local_path: str,
        overwrite: bool = False,
    ) -> dict:
        """Download a file from a remote SSH host to the MCP server filesystem.

        In STDIO mode, local_path is on the client machine running this MCP
        server. In HTTP mode, local_path is on the remote MCP server host.
        The local path must be under the configured allowed_local_paths.

        Args:
            host: Name of the host
            remote_path: Source file path on the remote SSH host
            local_path: Destination path on the MCP server filesystem
            overwrite: Whether to overwrite an existing local file

        Returns:
            Dictionary containing transfer metadata, bytes, SHA-256, and success.
        """
        return service.download_file(host, remote_path, local_path, overwrite)

    @mcp.tool()
    def upload_file(
        host: str,
        local_path: str,
        remote_path: str,
        overwrite: bool = False,
    ) -> dict:
        """Upload a file from the MCP server filesystem to a remote SSH host.

        In STDIO mode, local_path is on the client machine running this MCP
        server. In HTTP mode, local_path is on the remote MCP server host.
        The local path must be under the configured allowed_local_paths, and
        the remote destination must be under allowed_remote_write_paths.

        Args:
            host: Name of the host
            local_path: Source path on the MCP server filesystem
            remote_path: Destination path on the remote SSH host
            overwrite: Whether to overwrite an existing remote file

        Returns:
            Dictionary containing transfer metadata, bytes, SHA-256, and success.
        """
        return service.upload_file(host, local_path, remote_path, overwrite)

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

    logger.info(f"FastMCP server '{name}' created with SSH and SFTP tools")
    return mcp
