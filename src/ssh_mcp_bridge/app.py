"""Main application entry point."""

import argparse
import logging
import platform
import sys
from pathlib import Path
from typing import Optional

import fastmcp
import uvicorn

from ssh_mcp_bridge.models.config import load_config, Config
from ssh_mcp_bridge.core.session_manager import SshSessionManager
from ssh_mcp_bridge.services.mcp_service import McpService
from ssh_mcp_bridge.api.mcp_server import create_mcp_server
from ssh_mcp_bridge.api.http_server import create_http_server
from ssh_mcp_bridge.utils.logging import setup_logging

logger = logging.getLogger(__name__)

# Version info
VERSION = "2.0.0"


class Application:
    """Main application class."""

    def __init__(self, config: Config):
        """Initialize application.

        Args:
            config: Application configuration
        """
        self.config = config
        self.session_manager: Optional[SshSessionManager] = None
        self.service: Optional[McpService] = None
        self.mcp_server = None
        self.http_server = None

    def initialize(self):
        """Initialize all components."""
        logger.info("Initializing SSH MCP Bridge")

        # Initialize session manager
        self.session_manager = SshSessionManager(self.config)
        self.session_manager.start()
        logger.info(f"Session manager started with {len(self.config.hosts)} hosts")

        # Initialize service layer
        self.service = McpService(self.session_manager)
        logger.info("Service layer initialized")

        # Initialize MCP server
        self.mcp_server = create_mcp_server(self.service, "SSH Bridge")

        # Initialize HTTP server if enabled
        if self.config.server.enable_http:
            self.http_server = create_http_server(self.service, self.config.server)
            logger.info(
                f"HTTP server initialized on {self.config.server.host}:{self.config.server.port}"
            )

        logger.info("Application initialized successfully")

    def run(self):
        """Run the application."""
        if not self.service:
            raise RuntimeError("Application not initialized. Call initialize() first.")

        if self.config.server.enable_http and self.config.server.enable_stdio:
            logger.error("Cannot run both HTTP and STDIO modes simultaneously")
            logger.error("Please choose one mode or run separate instances")
            sys.exit(1)

        if self.config.server.enable_http:
            self._run_http()
        elif self.config.server.enable_stdio:
            self._run_stdio()
        else:
            logger.error("No transport mode enabled. Set enable_http or enable_stdio to true")
            sys.exit(1)

    def _run_http(self):
        """Run in HTTP mode."""
        logger.info("Starting HTTP server mode")
        logger.info(f"API available at http://{self.config.server.host}:{self.config.server.port}")
        logger.info(f"Health check: http://{self.config.server.host}:{self.config.server.port}/health")
        logger.info(f"API docs: http://{self.config.server.host}:{self.config.server.port}/docs")

        uvicorn.run(
            self.http_server,
            host=self.config.server.host,
            port=self.config.server.port,
            log_level=self.config.server.log_level.lower(),
        )

    def _run_stdio(self):
        """Run in STDIO mode."""
        logger.info("Starting STDIO (MCP) mode")
        logger.info("Server ready for MCP client connections")
        self.mcp_server.run()

    def shutdown(self):
        """Shutdown the application gracefully."""
        logger.info("Shutting down application")
        if self.session_manager:
            self.session_manager.stop()
        logger.info("Application shutdown complete")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="SSH MCP Bridge - Enterprise SSH gateway for AI assistants",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # STDIO mode (for Claude Desktop, etc.)
  %(prog)s config.yaml

  # HTTP mode
  %(prog)s --http config.yaml

  # Custom log level
  %(prog)s --log-level DEBUG config.yaml

Environment Variables:
  SSH_MCP_CONFIG    Path to configuration file
  SSH_MCP_MODE      Transport mode (stdio or http)
  SSH_MCP_LOG_LEVEL Logging level
        """,
    )

    parser.add_argument(
        "config",
        nargs="?",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    parser.add_argument(
        "--mode",
        choices=["stdio", "http"],
        help="Transport mode (overrides config file)",
    )

    parser.add_argument(
        "--http",
        action="store_true",
        help="Run in HTTP mode (shortcut for --mode http)",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARN", "ERROR"],
        help="Logging level (overrides config file)",
    )

    parser.add_argument(
        "--log-file",
        type=Path,
        help="Path to log file (default: stderr only)",
    )

    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version information",
    )

    args = parser.parse_args()

    # Handle --version flag
    if args.version:
        print(f"SSH MCP Bridge version:                    {VERSION}")
        print(f"FastMCP version:                           {fastmcp.__version__}")
        try:
            import mcp
            print(f"MCP version:                               {mcp.__version__}")
        except (ImportError, AttributeError):
            print("MCP version:                               N/A")
        print(f"Python version:                            {platform.python_version()}")
        print(f"Platform:                                  {platform.platform()}")
        sys.exit(0)

    return args


def main():
    """Main entry point."""
    args = parse_args()

    # Setup basic logging first
    log_level = args.log_level or "INFO"
    setup_logging(level=log_level, log_file=args.log_file)

    logger.info("=" * 60)
    logger.info(f"SSH MCP Bridge v{VERSION} - Enterprise Edition")
    logger.info(f"FastMCP v{fastmcp.__version__}")
    logger.info("=" * 60)

    try:
        # Load configuration
        config_path = Path(args.config)
        if not config_path.exists():
            logger.error(f"Configuration file not found: {config_path}")
            sys.exit(1)

        config = load_config(config_path)
        logger.info(f"Configuration loaded from {config_path}")

        # Override mode if specified
        if args.http or args.mode == "http":
            config.server.enable_http = True
            config.server.enable_stdio = False
        elif args.mode == "stdio":
            config.server.enable_stdio = True
            config.server.enable_http = False

        # Override log level if specified
        if args.log_level:
            config.server.log_level = args.log_level
            setup_logging(level=args.log_level, log_file=args.log_file)

        # Create and run application
        app = Application(config)
        app.initialize()

        logger.info("Starting application")
        app.run()

    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        if "app" in locals():
            app.shutdown()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
