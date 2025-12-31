# Installation Guide

Complete installation guide for SSH MCP Bridge with multiple deployment options.

## Prerequisites

- **Python 3.9+** (Python 3.12+ recommended)
- **SSH access** to your servers with key-based authentication
- **Git** for cloning the repository
- **Docker** (optional, for container deployment)

## System Requirements

### Minimum Requirements
- **CPU**: 1 core
- **RAM**: 512 MB
- **Disk**: 100 MB
- **Network**: Access to SSH servers (port 22)

### Recommended Requirements
- **CPU**: 2 cores
- **RAM**: 1 GB
- **Disk**: 500 MB
- **Network**: Low latency connection to SSH servers

## Installation Methods

### Method 1: Python Virtual Environment (Recommended for Local Use)

```bash
# Clone the repository
git clone https://github.com/shashikanth-gs/mcp-ssh-bridge.git
cd ssh-mcp-bridge

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -m ssh_mcp_bridge --version
```

### Method 2: Docker (Recommended for Production)

```bash
# Pull the official image
docker pull shashikanth-gs/mcp-ssh-bridge:latest

# Or build from source
git clone https://github.com/shashikanth-gs/mcp-ssh-bridge.git
cd ssh-mcp-bridge
docker build -t ssh-mcp-bridge:latest .
```

### Method 3: Docker Compose (Easiest for Production)

```bash
# Clone repository
git clone https://github.com/shashikanth-gs/mcp-ssh-bridge.git
cd ssh-mcp-bridge

# Create configuration
cp examples/config.http.yaml config.yaml
# Edit config.yaml with your settings

# Start service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop service
docker-compose down
```

### Method 4: Development Installation

For development or contributing:

```bash
# Clone repository
git clone https://github.com/shashikanth-gs/mcp-ssh-bridge.git
cd ssh-mcp-bridge

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks (if configured)
pre-commit install

# Run tests
pytest
```

## Verifying Installation

### Python Installation

```bash
# Check Python version
python --version  # Should be 3.9 or higher

# Verify module imports
python -c "import ssh_mcp_bridge; print('Installation successful')"

# Check dependencies
pip list | grep -E "paramiko|fastmcp|fastapi|pyyaml"
```

### Docker Installation

```bash
# Check Docker version
docker --version

# Verify image
docker images | grep ssh-mcp-bridge

# Test container
docker run --rm ssh-mcp-bridge:latest --version
```

## Configuration

### Creating Configuration File

```bash
# For STDIO mode (local deployment)
cp examples/config.stdio.yaml config.yaml

# For HTTP mode (remote deployment)
cp examples/config.http.yaml config.yaml

# For OAuth authentication
cp examples/config.oauth.yaml config.yaml

# Edit configuration
nano config.yaml  # or vim, code, etc.
```

### Minimal Configuration

Create a file named `config.yaml`:

```yaml
server:
  enable_stdio: true
  enable_http: false
  log_level: "INFO"

hosts:
  - name: example-server
    description: "Example SSH server"
    host: "example.com"
    username: "user"
    private_key_path: "~/.ssh/id_rsa"
    execution_mode: "shell"

session:
  idle_timeout: 30
  max_sessions_per_host: 5
```

### Setting Up SSH Keys

```bash
# Generate SSH key if you don't have one
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa

# Copy key to remote server
ssh-copy-id -i ~/.ssh/id_rsa.pub user@example.com

# Test connection
ssh -i ~/.ssh/id_rsa user@example.com

# Set correct permissions
chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_rsa
chmod 644 ~/.ssh/id_rsa.pub
```

## Running SSH MCP Bridge

### STDIO Mode (Local Deployment)

```bash
# Activate virtual environment
source .venv/bin/activate

# Run server
python -m ssh_mcp_bridge

# With custom config location
python -m ssh_mcp_bridge /path/to/config.yaml

# With debug logging
python -m ssh_mcp_bridge --log-level DEBUG config.yaml
```

### HTTP Mode (Remote Deployment)

```bash
# Run HTTP server
python -m ssh_mcp_bridge --http

# Specify mode explicitly
python -m ssh_mcp_bridge --mode http config.yaml

# With custom port (set in config.yaml)
python -m ssh_mcp_bridge --http
```

### Docker Deployment

```bash
# Run with volume mounts
docker run -d \
  --name ssh-mcp-bridge \
  -p 8080:8080 \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v ~/.ssh:/home/mcpuser/.ssh:ro \
  --restart unless-stopped \
  shashikanth-gs/mcp-ssh-bridge:latest

# View logs
docker logs -f ssh-mcp-bridge

# Stop container
docker stop ssh-mcp-bridge

# Remove container
docker rm ssh-mcp-bridge
```

## Platform-Specific Instructions

### macOS

```bash
# Install Python 3.12 using Homebrew
brew install python@3.12

# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install SSH MCP Bridge
pip install -r requirements.txt
```

### Linux (Ubuntu/Debian)

```bash
# Install Python 3.9+
sudo apt update
sudo apt install python3 python3-pip python3-venv

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install SSH MCP Bridge
pip install -r requirements.txt
```

### Linux (RHEL/CentOS/Fedora)

```bash
# Install Python 3.9+
sudo dnf install python3 python3-pip

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install SSH MCP Bridge
pip install -r requirements.txt
```

### Windows

```powershell
# Install Python from python.org (3.9+)

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install SSH MCP Bridge
pip install -r requirements.txt
```

## Dependency Information

### Core Dependencies

- **paramiko** - SSH protocol implementation
- **pyyaml** - YAML configuration parsing
- **fastmcp** - MCP protocol framework
- **fastapi** - HTTP API framework (for HTTP mode)
- **uvicorn** - ASGI server (for HTTP mode)
- **pyjwt** - JWT token verification (for OAuth)
- **cryptography** - Cryptographic functions

### Development Dependencies

- **pytest** - Testing framework
- **pytest-cov** - Code coverage
- **pytest-asyncio** - Async test support
- **black** - Code formatter
- **flake8** - Code linter
- **mypy** - Type checker

## Upgrading

### Upgrading Python Installation

```bash
# Activate virtual environment
source .venv/bin/activate

# Pull latest changes
git pull origin main

# Upgrade dependencies
pip install --upgrade -r requirements.txt

# Restart the server
```

### Upgrading Docker Installation

```bash
# Pull latest image
docker pull shashikanth-gs/mcp-ssh-bridge:latest

# Stop current container
docker stop ssh-mcp-bridge
docker rm ssh-mcp-bridge

# Start with new image
docker run -d \
  --name ssh-mcp-bridge \
  -p 8080:8080 \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v ~/.ssh:/home/mcpuser/.ssh:ro \
  shashikanth-gs/mcp-ssh-bridge:latest
```

## Uninstallation

### Python Installation

```bash
# Deactivate virtual environment
deactivate

# Remove virtual environment
rm -rf .venv

# Remove cloned repository
cd ..
rm -rf ssh-mcp-bridge
```

### Docker Installation

```bash
# Stop and remove container
docker stop ssh-mcp-bridge
docker rm ssh-mcp-bridge

# Remove image
docker rmi shashikanth-gs/mcp-ssh-bridge:latest

# Remove docker-compose setup
docker-compose down
```

## Troubleshooting

### Python Import Errors

```bash
# Verify Python version
python --version

# Check if module is installed
pip show ssh-mcp-bridge

# Reinstall dependencies
pip install --force-reinstall -r requirements.txt
```

### Permission Errors

```bash
# Fix SSH key permissions
chmod 600 ~/.ssh/id_rsa
chmod 600 config.yaml

# Fix Python package permissions
pip install --user -r requirements.txt
```

### Docker Issues

```bash
# Check Docker status
docker ps -a

# View container logs
docker logs ssh-mcp-bridge

# Check image
docker inspect shashikanth-gs/mcp-ssh-bridge:latest

# Rebuild image
docker build --no-cache -t ssh-mcp-bridge:latest .
```

### Network Issues

```bash
# Test SSH connectivity
ssh -v -i ~/.ssh/id_rsa user@host

# Check port availability
netstat -an | grep 8080

# Test HTTP server
curl http://localhost:8080/health
```

## Next Steps

- Configure your [MCP client integration](QUICKSTART.md)
- Review [configuration options](CONFIGURATION.md)
- Set up [OAuth authentication](CHATGPT_INTEGRATION.md)
- Learn about [Docker deployment](DOCKER.md)
- Read [security best practices](SECURITY.md)
