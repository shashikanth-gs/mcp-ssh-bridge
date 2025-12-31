# SSH MCP Bridge

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://hub.docker.com/r/shashikanthg/mcp-ssh-bridge)

**Securely orchestrate infrastructure across multiple SSH servers using AI agents.** SSH MCP Bridge enables AI assistants like Claude, ChatGPT, and VS Code Copilot to manage servers, deploy applications, and troubleshoot issues—all without exposing credentials or infrastructure secrets.

## What is SSH MCP Bridge?

SSH MCP Bridge is a [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that provides AI agents with secure, auditable SSH access to multiple servers. It acts as a gateway between AI assistants and your infrastructure, enabling:

- **Multi-server orchestration** - Coordinate actions across reverse proxies, application servers, databases, and supporting services
- **Credential isolation** - AI agents never see IPs, passwords, or SSH keys
- **Full auditability** - Track all commands executed across your infrastructure
- **Self-discovery** - Agents automatically discover available servers and their capabilities
- **Goal-oriented automation** - Agents can deploy apps, configure services, and resolve issues autonomously

## Use Cases

### Homelab & Self-Hosted Infrastructure
- Automate server maintenance and updates
- Deploy applications across multiple nodes
- Configure reverse proxies and SSL certificates
- Manage Docker containers and Kubernetes clusters
- Monitor and troubleshoot issues

### Enterprise Infrastructure
- Cross-server deployment orchestration
- Database schema migrations
- Service configuration management
- Infrastructure troubleshooting
- Compliance and audit logging

### Example Scenarios

**Scenario 1: Deploy a Web Application**
An agent can:
1. Create database tables on your database server
2. Deploy application code on your app server
3. Configure reverse proxy rules on your proxy server
4. Verify the deployment is working correctly

**Scenario 2: Troubleshoot Performance Issues**
An agent can:
1. Check system resources across all servers
2. Analyze application logs
3. Review database query performance
4. Identify bottlenecks and suggest optimizations

## Key Features

| Feature | Description |
|---------|-------------|
| **Dual Transport** | STDIO (local) + HTTP/SSE (remote) deployment modes |
| **Security First** | OAuth 2.0/OIDC authentication, credential isolation |
| **Auditability** | Complete logging of all SSH commands and sessions |
| **Self-Discovery** | Servers advertise their capabilities to agents |
| **Multi-Server** | Orchestrate across unlimited SSH hosts |
| **Production Ready** | Docker deployment, health checks, session management |
| **Scalable** | Session pooling, automatic cleanup, resource limits |
| **Universal MCP** | Works with Claude Desktop, VS Code, ChatGPT, and any MCP client |

## Prerequisites

- **Python 3.9+** (Python 3.12+ recommended)
- **SSH access** to your servers with key-based authentication
- One of:
  - **Claude Desktop** (for local use)
  - **VS Code with Copilot** (for local use)
  - **ChatGPT** (for remote HTTP deployment)
  - Any MCP-compatible client

## Quick Start

### Local Deployment (STDIO Mode)

Perfect for homelabs where your machine has direct SSH access to all servers.

```bash
# 1. Clone the repository
git clone https://github.com/shashikanth-gs/mcp-ssh-bridge.git
cd ssh-mcp-bridge

# 2. Install dependencies
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Create configuration
cp examples/config.stdio.yaml config.yaml
# Edit config.yaml with your SSH hosts

# 4. Configure your MCP client (see integration guides below)
```

### Remote Deployment (HTTP Mode)

Deploy alongside your servers for remote AI agent access.

```bash
# Using Docker (recommended)
docker pull shashikanth-gs/mcp-ssh-bridge:latest

docker run -d \
  --name ssh-mcp-bridge \
  -p 8080:8080 \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v ~/.ssh:/home/mcpuser/.ssh:ro \
  shashikanth-gs/mcp-ssh-bridge:latest

# Access via HTTP/SSE at http://your-server:8080
```

## Configuration

### Minimal Configuration Example

```yaml
server:
  enable_stdio: true        # For local deployment
  enable_http: false        # Set to true for remote deployment
  log_level: "INFO"

hosts:
  - name: web-server
    description: "Production web server with Nginx"
    host: "192.168.1.100"
    username: "admin"
    private_key_path: "~/.ssh/id_rsa"
    execution_mode: "shell"

  - name: db-server
    description: "PostgreSQL database server"
    host: "192.168.1.101"
    username: "dbadmin"
    private_key_path: "~/.ssh/db_key"
    execution_mode: "exec"

session:
  idle_timeout: 30
  max_sessions_per_host: 5
```

See [examples/](examples/) for more configuration options including OAuth setup.

## Integration Guides

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ssh-bridge": {
      "command": "/path/to/ssh-mcp-bridge/.venv/bin/python",
      "args": ["-m", "ssh_mcp_bridge", "/path/to/config.yaml"]
    }
  }
}
```

Replace `/path/to/ssh-mcp-bridge/.venv/bin/python` with your actual venv Python path.

Restart Claude Desktop and ask: "List all available SSH hosts"

### VS Code with GitHub Copilot

1. Install the MCP extension for VS Code
2. Configure in VS Code settings:

```json
{
  "mcp.servers": {
    "ssh-bridge": {
      "command": "/path/to/ssh-mcp-bridge/.venv/bin/python",
      "args": ["-m", "ssh_mcp_bridge", "/path/to/config.yaml"]
    }
  }
}
```

### ChatGPT (Remote HTTP/OAuth)

See [docs/CHATGPT_INTEGRATION.md](docs/CHATGPT_INTEGRATION.md) for detailed OAuth setup with Auth0, Azure AD, or other OIDC providers.

## Available MCP Tools

Agents can use these tools to interact with your servers:

- **`list_hosts()`** - Discover available SSH servers
- **`execute_command(host, command)`** - Execute commands on specific servers
- **`get_working_directory(host)`** - Get current working directory
- **`close_session(host)`** - Close SSH session
- **`get_session_stats()`** - View active sessions and statistics

## Documentation

- **[Quick Start Guide](docs/QUICKSTART.md)** - Get running in 5 minutes
- **[Installation Guide](docs/INSTALLATION.md)** - Detailed installation instructions
- **[Configuration Reference](docs/CONFIGURATION.md)** - All configuration options
- **[Docker Deployment](docs/DOCKER.md)** - Container deployment guide
- **[ChatGPT Integration](docs/CHATGPT_INTEGRATION.md)** - OAuth setup for ChatGPT
- **[Architecture Overview](docs/ARCHITECTURE.md)** - Technical deep dive
- **[Security Best Practices](docs/SECURITY.md)** - Securing your deployment

## Docker Deployment

```bash
# Pull the image
docker pull shashikanth-gs/mcp-ssh-bridge:latest

# Run with your configuration
docker run -d \
  --name ssh-mcp-bridge \
  -p 8080:8080 \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v ~/.ssh:/home/mcpuser/.ssh:ro \
  shashikanth-gs/mcp-ssh-bridge:latest

# Health check
curl http://localhost:8080/health
```

See [docs/DOCKER.md](docs/DOCKER.md) for more deployment options.

## Security

- **No credential exposure**: SSH credentials stay server-side only
- **OAuth 2.0 support**: Integrate with Auth0, Azure AD, Keycloak, etc.
- **Audit logging**: All commands logged with timestamps and user context
- **Session isolation**: Each host maintains independent sessions
- **Non-root containers**: Docker images run as unprivileged user
- **Configurable access**: Control which servers agents can access

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone and setup
git clone https://github.com/shashikanth-gs/mcp-ssh-bridge.git
cd ssh-mcp-bridge
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest
```

## License

MIT License - See [LICENSE](LICENSE) for details.

## Credits

Created by **Shashi Kanth G S** ([@shashikanth-gs](https://github.com/shashikanth-gs))

Built with:
- [FastMCP](https://github.com/jlowin/fastmcp) - MCP framework
- [Paramiko](https://www.paramiko.org/) - SSH implementation
- [FastAPI](https://fastapi.tiangolo.com/) - HTTP API framework

## Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/shashikanth-gs/mcp-ssh-bridge/issues)
- **Discussions**: [GitHub Discussions](https://github.com/shashikanth-gs/mcp-ssh-bridge/discussions)

## Roadmap

- [ ] File transfer support (SCP/SFTP)
- [ ] Multi-hop SSH (bastion/jump hosts)
- [ ] Resource definitions for server state
- [ ] Prompt templates for common operations
- [ ] WebSocket support for real-time streaming
- [ ] Prometheus metrics export

---

**If you find this project useful, please star it on GitHub!**
