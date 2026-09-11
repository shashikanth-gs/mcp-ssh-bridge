"""Regression coverage for every exposed MCP tool."""

import asyncio

from ssh_mcp_bridge.api.mcp_server import create_mcp_server
from ssh_mcp_bridge.models.results import CommandResult


class RecordingService:
    """Service double that records every MCP tool dispatch."""

    def __init__(self):
        self.calls = []

    def record(self, name, args, result):
        self.calls.append((name, args))
        return result

    def list_hosts(self):
        return self.record("list_hosts", (), [{"name": "host", "description": "test"}])

    def execute_command(self, host, command):
        return self.record(
            "execute_command",
            (host, command),
            CommandResult(host=host, output="done", success=True, exit_status=0),
        )

    def get_working_directory(self, host):
        return self.record(
            "get_working_directory", (host,), {"host": host, "working_directory": "/srv"}
        )

    def get_file_transfer_config(self):
        return self.record("get_file_transfer_config", (), {"mode": "server-side"})

    def stat_remote_path(self, host, remote_path):
        return self.record(
            "stat_remote_path",
            (host, remote_path),
            {"host": host, "path": remote_path, "type": "file"},
        )

    def list_remote_directory(self, host, remote_path, limit):
        return self.record(
            "list_remote_directory",
            (host, remote_path, limit),
            {"host": host, "path": remote_path, "entries": []},
        )

    def download_file(self, host, remote_path, local_path, overwrite):
        return self.record(
            "download_file",
            (host, remote_path, local_path, overwrite),
            {"host": host, "remote_path": remote_path, "local_path": local_path},
        )

    def upload_file(self, host, local_path, remote_path, overwrite):
        return self.record(
            "upload_file",
            (host, local_path, remote_path, overwrite),
            {"host": host, "local_path": local_path, "remote_path": remote_path},
        )

    def close_session(self, host):
        return self.record("close_session", (host,), {"host": host, "message": "closed"})

    def get_session_stats(self):
        return self.record("get_session_stats", (), {"total_sessions": 0})


def test_every_mcp_tool_is_registered_and_dispatches_to_service():
    service = RecordingService()
    mcp = create_mcp_server(service)

    async def exercise_tools():
        tools = await mcp.list_tools()
        assert {tool.name for tool in tools} == {
            "list_hosts",
            "execute_command",
            "get_working_directory",
            "get_file_transfer_config",
            "stat_remote_path",
            "list_remote_directory",
            "download_file",
            "upload_file",
            "close_session",
            "get_session_stats",
        }

        calls = [
            ("list_hosts", {}),
            ("execute_command", {"host": "host", "command": "uptime"}),
            ("get_working_directory", {"host": "host"}),
            ("get_file_transfer_config", {}),
            ("stat_remote_path", {"host": "host", "remote_path": "/tmp/file"}),
            (
                "list_remote_directory",
                {"host": "host", "remote_path": "/tmp", "limit": 10},
            ),
            (
                "download_file",
                {
                    "host": "host",
                    "remote_path": "/tmp/file",
                    "local_path": "/tmp/file",
                    "overwrite": True,
                },
            ),
            (
                "upload_file",
                {
                    "host": "host",
                    "local_path": "/tmp/file",
                    "remote_path": "/tmp/file",
                    "overwrite": True,
                },
            ),
            ("close_session", {"host": "host"}),
            ("get_session_stats", {}),
        ]
        for name, arguments in calls:
            result = await mcp.call_tool(name, arguments)
            assert result.is_error is False

    asyncio.run(exercise_tools())

    assert service.calls == [
        ("list_hosts", ()),
        ("execute_command", ("host", "uptime")),
        ("get_working_directory", ("host",)),
        ("get_file_transfer_config", ()),
        ("stat_remote_path", ("host", "/tmp/file")),
        ("list_remote_directory", ("host", "/tmp", 10)),
        ("download_file", ("host", "/tmp/file", "/tmp/file", True)),
        ("upload_file", ("host", "/tmp/file", "/tmp/file", True)),
        ("close_session", ("host",)),
        ("get_session_stats", ()),
    ]
