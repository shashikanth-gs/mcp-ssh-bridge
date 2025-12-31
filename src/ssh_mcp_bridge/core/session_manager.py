"""SSH session pool manager."""

import logging
import threading
import time
from collections import defaultdict
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
