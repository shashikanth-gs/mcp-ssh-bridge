# File Transfer Guide

SSH MCP Bridge supports bidirectional file transfer using SFTP over the same SSH host definitions used for command execution.

## Mental Model

There are three possible machines in a deployment:

- **MCP client**: Codex, Claude, ChatGPT, VS Code, or another MCP client.
- **MCP server host**: the machine running `ssh-mcp-bridge`.
- **SSH target host**: a configured host such as `web-server`, `neptune`, or `k3s-aio-01`.

The transfer tools move files between the MCP server host and an SSH target host:

```text
download_file: SSH target host -> MCP server host
upload_file:   MCP server host -> SSH target host
```

## STDIO Mode

In STDIO mode, the MCP client and `ssh-mcp-bridge` usually run on the same machine.

```text
Codex or Claude laptop
  runs ssh-mcp-bridge over stdio
  local_path means laptop filesystem
    |
    | SFTP
    v
SSH target host
```

Example:

```text
upload_file(
  host="web-server",
  local_path="/Users/me/Downloads/app.env",
  remote_path="/tmp/app.env"
)
```

Here `/Users/me/Downloads/app.env` is on the laptop running the MCP client.

## HTTP Mode

In HTTP mode, the MCP client connects to a remote `ssh-mcp-bridge` process.

```text
Laptop, ChatGPT, or another MCP client
  connects over HTTP
    |
    v
MCP server host
  local_path means this server filesystem
    |
    | SFTP
    v
SSH target host
```

Example:

```text
upload_file(
  host="web-server",
  local_path="/var/lib/ssh-mcp-bridge/transfers/app.env",
  remote_path="/tmp/app.env"
)
```

Here `/var/lib/ssh-mcp-bridge/transfers/app.env` must already exist on the MCP server host. It is not read from the laptop that connected over HTTP.

The HTTP API exposes transfer operations through:

- `GET /api/v1/file-transfer-config`
- `POST /api/v1/remote/stat`
- `POST /api/v1/remote/list`
- `POST /api/v1/download`
- `POST /api/v1/upload`

Those endpoints trigger SFTP transfers from the bridge host. They do not stream
browser/laptop file bytes directly into the SSH target.

For remote HTTP deployments, use a staging directory:

```yaml
security:
  allowed_local_paths:
    - "/var/lib/ssh-mcp-bridge/transfers"
  allowed_remote_write_paths:
    - "~"
    - "/tmp"
  max_file_transfer_mb: 100
```

A separate upload channel can place files into the staging directory. The MCP tool then transfers from that staging directory to the SSH target host.

## Tools

### `get_file_transfer_config`

Returns the active file-transfer policy and explains the server-side path semantics.

### `stat_remote_path`

Gets metadata for a remote file or directory:

```text
stat_remote_path(host="web-server", remote_path="/tmp/app.env")
```

### `list_remote_directory`

Lists remote directory entries:

```text
list_remote_directory(host="web-server", remote_path="/tmp", limit=100)
```

### `download_file`

Downloads a file from an SSH target host to the MCP server host:

```text
download_file(
  host="web-server",
  remote_path="/var/log/nginx/error.log",
  local_path="/tmp/error.log",
  overwrite=true
)
```

The result includes transfer metadata:

```json
{
  "host": "web-server",
  "remote_path": "/var/log/nginx/error.log",
  "local_path": "/tmp/error.log",
  "bytes": 12345,
  "sha256": "..."
}
```

### `upload_file`

Uploads a file from the MCP server host to an SSH target host:

```text
upload_file(
  host="web-server",
  local_path="/tmp/app.env",
  remote_path="/tmp/app.env",
  overwrite=true
)
```

## Safety Policy

Configure transfer limits in `config.yaml`:

```yaml
security:
  allowed_local_paths:
    - "~/Downloads"
    - "/tmp"
  allowed_remote_write_paths:
    - "~"
    - "/tmp"
  max_file_transfer_mb: 100
```

Rules:

- Upload sources must be under `allowed_local_paths`.
- Download destinations must be under `allowed_local_paths`.
- Remote upload destinations must be under `allowed_remote_write_paths`.
- Files larger than `max_file_transfer_mb` are rejected.
- Existing files are not overwritten unless `overwrite=true`.
- Directory transfers are intentionally not supported yet.

## Recommended Patterns

For local STDIO use:

```yaml
security:
  allowed_local_paths:
    - "~/Downloads"
    - "~/Desktop"
    - "/tmp"
  allowed_remote_write_paths:
    - "~"
    - "/tmp"
  max_file_transfer_mb: 100
```

For remote HTTP use:

```yaml
security:
  allowed_local_paths:
    - "/var/lib/ssh-mcp-bridge/transfers"
  allowed_remote_write_paths:
    - "~"
    - "/tmp"
  max_file_transfer_mb: 100
```

For production HTTP use, keep the staging directory owned by the bridge user, back it up only when needed, and prune old transfer files regularly.

## Current Limitations

- File transfer is single-file only.
- Remote-to-client direct download is not handled by MCP itself here.
- HTTP-mode browser/laptop binary upload still requires an external staging channel or a future multipart upload endpoint.
- Transfer results return metadata, not file contents.

Future improvements can add transfer IDs, expiring download URLs, object storage signed URLs, and MCP resource exposure for downloaded files.
