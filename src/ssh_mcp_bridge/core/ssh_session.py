"""SSH session management."""

import logging
import socket
import time
import uuid
from typing import Any, Dict, Optional

import paramiko

logger = logging.getLogger(__name__)


class SshConnectionError(Exception):
    """SSH connection error with user-friendly messages."""

    def __init__(self, host_name: str, original_error: Exception):
        self.host_name = host_name
        self.original_error = original_error
        self.message = self._create_friendly_message(original_error)
        super().__init__(self.message)

    def _create_friendly_message(self, error: Exception) -> str:
        """Create user-friendly error message."""
        error_str = str(error)

        if "Network is unreachable" in error_str or "Errno 51" in error_str:
            return f"Connection to '{self.host_name}' failed: Network is unreachable"
        if "nodename nor servname provided" in error_str or "Errno 8" in error_str:
            return f"Connection to '{self.host_name}' failed: Host not found"
        if "Connection refused" in error_str or "Errno 111" in error_str or "Errno 61" in error_str:
            return f"Connection to '{self.host_name}' failed: Connection refused"
        if "timed out" in error_str.lower() or isinstance(error, socket.timeout):
            return f"Connection to '{self.host_name}' failed: Connection timed out"
        if isinstance(error, paramiko.AuthenticationException):
            return f"Connection to '{self.host_name}' failed: Authentication failed"
        if isinstance(error, paramiko.SSHException):
            return f"Connection to '{self.host_name}' failed: SSH protocol error - {error_str}"

        return f"Connection to '{self.host_name}' failed: {error_str}"


# Environment variables to disable pagers
PAGER_DISABLE_ENV = {
    "PAGER": "cat",
    "SYSTEMD_PAGER": "",
    "GIT_PAGER": "cat",
    "LESS": "-F -X -R",
    "MANPAGER": "cat",
    "BAT_PAGER": "",
}

PAGER_COMMANDS = {
    "journalctl": "--no-pager",
    "systemctl": "--no-pager",
    "git": "--no-pager",
}


class SshSession:
    """Manages a persistent SSH connection."""

    def __init__(self, host_config, execution_mode: str = "exec", disable_pager: bool = True):
        self.host_config = host_config
        self.execution_mode = execution_mode
        self.disable_pager = disable_pager
        self.client: Optional[paramiko.SSHClient] = None
        self.shell_channel: Optional[paramiko.Channel] = None
        self.last_access = time.time()
        self.connected = False

    def connect(self):
        """Establish SSH connection."""
        if self.connected:
            return

        logger.info(f"Connecting to {self.host_config.name} ({self.host_config.host})")

        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_kwargs = {
            "hostname": self.host_config.host,
            "port": self.host_config.port,
            "username": self.host_config.username,
            "timeout": 60,
            "banner_timeout": 60,
            "auth_timeout": 60,
            "look_for_keys": False,
            "allow_agent": False,
        }

        if self.host_config.private_key_path:
            try:
                pkey = paramiko.RSAKey.from_private_key_file(self.host_config.private_key_path)
                connect_kwargs["pkey"] = pkey
            except Exception:
                try:
                    pkey = paramiko.Ed25519Key.from_private_key_file(self.host_config.private_key_path)
                    connect_kwargs["pkey"] = pkey
                except Exception as e:
                    raise SshConnectionError(self.host_config.name, e)
        elif self.host_config.password:
            connect_kwargs["password"] = self.host_config.password

        try:
            self.client.connect(**connect_kwargs)
        except Exception as e:
            logger.info(f"SSH connection failed to {self.host_config.name}: {str(e)}")
            raise SshConnectionError(self.host_config.name, e)

        if self.execution_mode == "shell":
            self.shell_channel = self.client.invoke_shell(width=120, height=40)
            self.shell_channel.settimeout(1.0)
            time.sleep(1.0)

            # Drain initial output
            attempts = 0
            while attempts < 10:
                if self.shell_channel.recv_ready():
                    try:
                        self.shell_channel.recv(65535)
                        time.sleep(0.1)
                    except socket.timeout:
                        break
                else:
                    break
                attempts += 1

            # Disable echo
            self.shell_channel.send("stty -echo\n")
            time.sleep(0.3)
            while self.shell_channel.recv_ready():
                self.shell_channel.recv(65535)
                time.sleep(0.05)

        self.connected = True
        self.last_access = time.time()
        logger.info(f"Connected to {self.host_config.name}")

    def execute_command(self, command: str) -> Dict[str, Any]:
        """Execute command on SSH session."""
        if not self.connected:
            self.connect()

        self.last_access = time.time()

        try:
            if self.execution_mode == "exec":
                return self._execute_exec_mode(command)
            else:
                return self._execute_shell_mode(command)
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            self.close()
            raise

    def _preprocess_command(self, command: str) -> str:
        """Preprocess command to disable pagers."""
        if not self.disable_pager:
            return command

        command_parts = command.strip().split()
        if command_parts:
            base_cmd = command_parts[0]
            if base_cmd in PAGER_COMMANDS:
                pager_flag = PAGER_COMMANDS[base_cmd]
                if pager_flag and pager_flag not in command:
                    command = f"{base_cmd} {pager_flag} {' '.join(command_parts[1:])}"

        env_prefix = " ".join([f"{k}='{v}'" for k, v in PAGER_DISABLE_ENV.items()])
        return f"export {env_prefix}; {command}"

    def _execute_exec_mode(self, command: str) -> Dict[str, Any]:
        """Execute command in exec mode (stateless)."""
        processed_command = self._preprocess_command(command)
        logger.debug(f"[{self.host_config.name}] $ {command}")

        start_time = time.time()
        stdin, stdout, stderr = self.client.exec_command(processed_command, timeout=60)

        stdout_data = stdout.read().decode("utf-8", errors="replace")
        stderr_data = stderr.read().decode("utf-8", errors="replace")
        exit_status = stdout.channel.recv_exit_status()
        execution_time = time.time() - start_time

        output = stdout_data
        if stderr_data:
            output += "\n" + stderr_data

        success = exit_status == 0
        status_icon = "✓" if success else "✗"
        logger.info(
            f"[{self.host_config.name}] {status_icon} {command[:60]}{'...' if len(command) > 60 else ''} ({execution_time:.2f}s)"
        )

        result = {
            "host": self.host_config.name,
            "command": command,
            "output": output.strip(),
            "success": success,
        }

        if not success:
            result["exit_status"] = exit_status

        return result

    def _execute_shell_mode(self, command: str) -> Dict[str, Any]:
        """Execute command in shell mode (stateful)."""
        if not self.shell_channel:
            raise RuntimeError("Shell channel not available")

        logger.debug(f"[{self.host_config.name}] $ {command}")
        start_time = time.time()

        start_marker = f"__START_{uuid.uuid4().hex}__"
        end_marker = f"__END_{uuid.uuid4().hex}__"

        # Clear buffer
        while self.shell_channel.recv_ready():
            self.shell_channel.recv(65535)
            time.sleep(0.05)

        processed_command = self._preprocess_command(command)
        full_command = f"echo '{start_marker}'; {processed_command}; echo '{end_marker}'\n"
        self.shell_channel.send(full_command)

        # Collect output
        output = ""
        timeout = 60
        marker_found = False
        consecutive_empty_reads = 0
        max_empty_reads = 20

        while True:
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Command timed out after {timeout} seconds")

            try:
                if self.shell_channel.recv_ready():
                    chunk = self.shell_channel.recv(4096).decode("utf-8", errors="replace")
                    if chunk:
                        output += chunk
                        consecutive_empty_reads = 0
                        if end_marker in output:
                            marker_found = True
                            break
                    else:
                        consecutive_empty_reads += 1
                else:
                    consecutive_empty_reads += 1

                if consecutive_empty_reads >= max_empty_reads and end_marker in output:
                    marker_found = True
                    break

                time.sleep(0.1)
            except socket.timeout:
                consecutive_empty_reads += 1
                if consecutive_empty_reads >= max_empty_reads and end_marker in output:
                    marker_found = True
                    break

        # Extract content between markers
        if start_marker in output and end_marker in output:
            start_idx = output.find(start_marker) + len(start_marker)
            end_idx = output.find(end_marker)
            output = output[start_idx:end_idx]
        elif end_marker in output:
            output = output.split(end_marker)[0]

        # Clean up output
        lines = output.split("\n")
        cleaned_lines = []
        for line in lines:
            if not cleaned_lines and not line.strip():
                continue
            if command.strip() in line and len(cleaned_lines) == 0:
                continue
            if start_marker in line or end_marker in line:
                continue
            cleaned_lines.append(line)

        while cleaned_lines and not cleaned_lines[-1].strip():
            cleaned_lines.pop()

        output = "\n".join(cleaned_lines)
        execution_time = time.time() - start_time

        logger.info(
            f"[{self.host_config.name}] ✓ {command[:60]}{'...' if len(command) > 60 else ''} ({execution_time:.2f}s)"
        )

        return {
            "host": self.host_config.name,
            "command": command,
            "output": output,
            "success": True,
        }

    def get_working_directory(self) -> str:
        """Get current working directory."""
        result = self.execute_command("pwd")
        return result["output"].strip()

    def close(self):
        """Close SSH connection."""
        if self.shell_channel:
            try:
                self.shell_channel.close()
            except Exception:
                pass
            self.shell_channel = None

        if self.client:
            try:
                self.client.close()
            except Exception:
                pass
            self.client = None

        self.connected = False
        logger.info(f"Closed session to {self.host_config.name}")

    def is_idle(self, timeout_minutes: int) -> bool:
        """Check if session is idle."""
        idle_seconds = time.time() - self.last_access
        return idle_seconds > (timeout_minutes * 60)
