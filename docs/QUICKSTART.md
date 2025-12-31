# Quick Start Guide

Get SSH MCP Bridge running in 5 minutes.

## Installation

### Option 1: Using pip

```bash
# Clone the repository
git clone https://github.com/shashikanth-gs/mcp-ssh-bridge.git
cd ssh-mcp-bridge

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Option 2: Using Docker

```bash
# Pull the image
docker pull shashikanth-gs/mcp-ssh-bridge:latest
```

## Configuration

Create a configuration file with your SSH hosts:

```bash
# Copy example configuration
cp examples/config.stdio.yaml config.yaml

# Edit with your servers
nano config.yaml
```

Minimal configuration:

```yaml
server:
  enable_stdio: true
  enable_http: false
  log_level: "INFO"

hosts:
  - name: my-server
    description: "My development server"
    host: "example.com"
    username: "myuser"
    private_key_path: "~/.ssh/id_rsa"
    execution_mode: "shell"

session:
  idle_timeout: 30
  max_sessions_per_host: 5
```

## Running the Server

### STDIO Mode (Local)

```bash
# Start the server
python -m ssh_mcp_bridge
```

The server will start and wait for MCP client connections via STDIO.

### HTTP Mode (Remote)

```bash
# Start HTTP server
python -m ssh_mcp_bridge --http

# Or using Docker
docker run -d \
  --name ssh-mcp-bridge \
  -p 8080:8080 \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v ~/.ssh:/home/mcpuser/.ssh:ro \
  shashikanth-gs/mcp-ssh-bridge:latest
```

## Integrating with Claude Desktop

1. Edit Claude config file:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`

2. Add the SSH MCP Bridge configuration:

```json
{
  "mcpServers": {
    "ssh-bridge": {
      "command": "/full/path/to/ssh-mcp-bridge/.venv/bin/python",
      "args": ["-m", "ssh_mcp_bridge", "/full/path/to/config.yaml"]
    }
  }
}
```

Note: Use the Python from your virtual environment where you ran `pip install -e .`

3. Restart Claude Desktop

4. Test by asking Claude:
   - "List all available SSH hosts"
   - "Execute 'uptime' on my-server"
   - "What is the current working directory on my-server?"

## Integrating with VS Code

1. Install the MCP extension for VS Code (if available)

2. Add to your VS Code settings.json:

```json
{
  "mcp.servers": {
    "ssh-bridge": {
      "command": "python",
      "args": ["-m", "ssh_mcp_bridge", "/full/path/to/config.yaml"]
    }
  }
}
```

3. Use GitHub Copilot to interact with your servers

## Testing Your Setup

Once configured, you can ask your AI assistant to:

1. **List servers**:
   - "Show me all available SSH hosts"
   - "What servers can you access?"

2. **Execute commands**:
   - "Check the uptime on my-server"
   - "List files in /var/log on my-server"
   - "Show disk usage on all servers"

3. **Multi-server operations**:
   - "Check if nginx is running on my-server and postgres is running on db-server"
   - "Deploy my application: create database on db-server, then deploy code on my-server"

## Common Issues

### SSH Connection Fails

**Problem**: Cannot connect to SSH server

**Solution**:
1. Test SSH connection manually: `ssh -i ~/.ssh/id_rsa user@host`
2. Verify SSH key permissions: `chmod 600 ~/.ssh/id_rsa`
3. Check host is reachable: `ping host`
4. Enable debug logging in config: `log_level: "DEBUG"`

### Configuration Not Found

**Problem**: Server cannot find config.yaml

**Solution**:
1. Use absolute path in MCP client configuration
2. Verify file exists: `ls -la /path/to/config.yaml`
3. Check file permissions: `chmod 600 config.yaml`

### MCP Client Cannot Connect

**Problem**: Claude/VS Code cannot connect to SSH MCP Bridge

**Solution**:
1. Verify PYTHONPATH is set correctly in MCP client config
2. Check Python can import module: `python -c "import ssh_mcp_bridge"`
3. Review MCP client logs for errors
4. Restart the MCP client application

### Session Timeouts

**Problem**: SSH sessions timeout too quickly

**Solution**:
1. Increase timeout in config: `idle_timeout: 60`
2. Use `execution_mode: shell` for persistent sessions
3. Close idle sessions manually when done

## Next Steps

- Read the [Installation Guide](INSTALLATION.md) for advanced setup
- Explore [Configuration Reference](CONFIGURATION.md) for all options
- Set up [OAuth authentication](CHATGPT_INTEGRATION.md) for ChatGPT
- Review [Security Best Practices](SECURITY.md)
- Learn about the [Architecture](ARCHITECTURE.md)

## Getting Help

- Check the [full documentation](../README.md)
- Search [existing issues](https://github.com/shashikanth-gs/mcp-ssh-bridge/issues)
- Ask in [discussions](https://github.com/shashikanth-gs/mcp-ssh-bridge/discussions)
