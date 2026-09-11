"""Command result shape, status, and MCP serialization tests."""

import asyncio
import re
from types import SimpleNamespace

from ssh_mcp_bridge.api.mcp_server import create_mcp_server
from ssh_mcp_bridge.core.ssh_session import SshSession
from ssh_mcp_bridge.models.results import CommandResult


class FakeStream:
    """Paramiko-like command stream."""

    def __init__(self, data: str, exit_status: int | None = None):
        self.data = data.encode()
        if exit_status is not None:
            self.channel = SimpleNamespace(recv_exit_status=lambda: exit_status)

    def read(self):
        return self.data


class FakeExecClient:
    """Paramiko-like client for exec-mode tests."""

    def __init__(self, stdout: str, stderr: str, exit_status: int):
        self.stdout = stdout
        self.stderr = stderr
        self.exit_status = exit_status

    def exec_command(self, command: str, timeout: int):
        return (
            FakeStream(""),
            FakeStream(self.stdout, self.exit_status),
            FakeStream(self.stderr),
        )


class FakeShellChannel:
    """Paramiko-like shell that responds with a nonzero status marker."""

    def __init__(self, output: str, exit_status: int):
        self.output = output
        self.exit_status = exit_status
        self.buffer = b""

    def recv_ready(self):
        return bool(self.buffer)

    def recv(self, size: int):
        chunk, self.buffer = self.buffer[:size], self.buffer[size:]
        return chunk

    def send(self, command: str):
        start_marker = re.search(r"__START_[0-9a-f]+__", command).group()
        end_marker = re.search(r"__END_[0-9a-f]+__", command).group()
        self.buffer = f"{start_marker}\n{self.output}\n{end_marker}:{self.exit_status}\n".encode()
        return len(command)

    def close(self):
        pass


def make_session(mode: str) -> SshSession:
    """Create a connected session without opening a network connection."""
    host = SimpleNamespace(name="test-host")
    session = SshSession(host, execution_mode=mode, disable_pager=False)
    session.connected = True
    return session


def test_exec_result_omits_command_and_always_includes_exit_status(caplog):
    secret_command = "deploy --token super-secret"
    session = make_session("exec")
    session.client = FakeExecClient("done", "", 0)

    with caplog.at_level("DEBUG"):
        result = session.execute_command(secret_command)

    assert result == CommandResult(host="test-host", output="done", success=True, exit_status=0)
    assert "command" not in result.model_dump()
    assert secret_command not in str(result.model_dump())
    assert secret_command not in caplog.text


def test_shell_result_reports_real_nonzero_exit_status_without_command(caplog):
    secret_command = "deploy --token super-secret"
    session = make_session("shell")
    session.shell_channel = FakeShellChannel("permission denied", 7)

    with caplog.at_level("DEBUG"):
        result = session.execute_command(secret_command)

    assert result == CommandResult(
        host="test-host",
        output="permission denied",
        success=False,
        exit_status=7,
    )
    assert "command" not in result.model_dump()
    assert secret_command not in str(result.model_dump())
    assert secret_command not in caplog.text


class FakeMcpService:
    """Service that supplies a typed command result to FastMCP."""

    def execute_command(self, host: str, command: str):
        return CommandResult(host=host, output="done", success=True, exit_status=0)

    def __getattr__(self, name):
        return lambda *args, **kwargs: {}


def test_fastmcp_exposes_typed_schema_and_compact_compatible_content():
    mcp = create_mcp_server(FakeMcpService())
    tool = next(tool for tool in asyncio.run(mcp.list_tools()) if tool.name == "execute_command")

    assert set(tool.output_schema["properties"]) == {
        "host",
        "output",
        "success",
        "exit_status",
    }

    result = asyncio.run(
        mcp.call_tool(
            "execute_command",
            {"host": "test-host", "command": "deploy --token super-secret"},
        )
    )

    assert "command" not in result.structured_content
    assert "super-secret" not in result.content[0].text
    assert result.structured_content["exit_status"] == 0
