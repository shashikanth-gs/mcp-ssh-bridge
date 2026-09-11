"""Typed results returned by MCP tools."""

from pydantic import BaseModel


class CommandResult(BaseModel):
    """Result of executing one SSH command."""

    host: str
    output: str
    success: bool
    exit_status: int
