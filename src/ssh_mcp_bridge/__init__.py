"""SSH MCP Bridge - Enterprise SSH gateway for AI assistants."""

__version__ = "2.0.0"
__author__ = "SSH MCP Bridge Team"
__description__ = "FastMCP-based SSH Bridge for Model Context Protocol with enterprise features"

from ssh_mcp_bridge.app import Application
from ssh_mcp_bridge.models.config import Config, HostConfig, SessionConfig, ServerConfig

__all__ = [
    "Application",
    "Config",
    "HostConfig",
    "SessionConfig",
    "ServerConfig",
    "__version__",
]
