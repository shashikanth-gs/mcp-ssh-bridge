# Configuration Reference

Complete configuration reference for SSH MCP Bridge.

## Configuration File Format

SSH MCP Bridge uses YAML format for configuration. The configuration file consists of three main sections:

1. `server` - Server and transport settings
2. `hosts` - SSH host definitions
3. `session` - Session management settings

## Configuration File Location

By default, SSH MCP Bridge looks for `config.yaml` in the current directory. You can specify a different location:

```bash
# Using command line argument
python -m ssh_mcp_bridge /path/to/config.yaml

# Using environment variable
export SSH_MCP_CONFIG=/path/to/config.yaml
python -m ssh_mcp_bridge
```

## Server Configuration

The `server` section configures transport modes and server behavior.

### Basic Server Settings

```yaml
server:
  host: "0.0.0.0"          # Listen address for HTTP mode
  port: 8080                # Port for HTTP mode
  enable_http: false        # Enable HTTP/SSE transport
  enable_stdio: true        # Enable STDIO transport
  log_level: "INFO"         # Logging level
```

### Server Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `host` | string | `"0.0.0.0"` | Address to bind HTTP server (HTTP mode only) |
| `port` | integer | `8080` | Port for HTTP server (HTTP mode only) |
| `enable_http` | boolean | `false` | Enable HTTP/SSE transport |
| `enable_stdio` | boolean | `true` | Enable STDIO transport |
| `log_level` | string | `"INFO"` | Logging level: DEBUG, INFO, WARN, ERROR |

### API Key Authentication (HTTP Mode)

For HTTP mode without OAuth:

```yaml
server:
  enable_http: true
  api_key: "your-secret-api-key-here"
  cors_origins:
    - "*"  # Or specific origins
```

**Security Note**: Use strong, randomly generated API keys. Example:
```bash
# Generate secure API key
openssl rand -hex 32
```

### OAuth/OIDC Authentication (HTTP Mode)

For enterprise authentication with OAuth 2.0/OIDC:

```yaml
server:
  enable_http: true
  oauth:
    enabled: true
    issuer: "https://your-domain.auth0.com/"
    audience: "https://your-api-identifier"
    jwks_uri: "https://your-domain.auth0.com/.well-known/jwks.json"  # Optional
```

OAuth configuration can also be set via environment variables:

```bash
export AUTH_MODE=oidc
export IDP_ISSUER=https://your-domain.auth0.com/
export IDP_AUDIENCE=https://your-api-identifier
export IDP_JWKS_URI=https://your-domain.auth0.com/.well-known/jwks.json
```

### CORS Configuration

```yaml
server:
  cors_origins:
    - "https://yourdomain.com"
    - "https://chat.openai.com"
    - "https://chatgpt.com"
  cors_allow_credentials: true
  cors_allow_methods:
    - "GET"
    - "POST"
  cors_allow_headers:
    - "Authorization"
    - "Content-Type"
```

## SSH Host Configuration

The `hosts` section defines SSH servers that agents can access.

### Basic Host Configuration

```yaml
hosts:
  - name: web-server
    description: "Production web server"
    host: "192.168.1.100"
    port: 22
    username: "admin"
    private_key_path: "~/.ssh/id_rsa"
    execution_mode: "shell"
    disable_pager: true
```

### Host Options

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `name` | string | Yes | - | Friendly name for the host (used by agents) |
| `description` | string | Yes | - | Description of the host purpose |
| `host` | string | Yes | - | Hostname or IP address |
| `port` | integer | No | `22` | SSH port |
| `username` | string | Yes | - | SSH username |
| `private_key_path` | string | No* | - | Path to SSH private key |
| `password` | string | No* | - | SSH password (not recommended) |
| `execution_mode` | string | No | `"exec"` | Execution mode: `exec` or `shell` |
| `disable_pager` | boolean | No | `true` | Disable pager for commands |

*One of `private_key_path` or `password` is required.

### Execution Modes

#### exec Mode (Stateless)

Each command runs in a fresh environment:

```yaml
hosts:
  - name: stateless-server
    execution_mode: "exec"
```

**Characteristics**:
- Each command runs independently
- No working directory persistence
- No environment variable persistence
- Faster for single commands
- Safer for untrusted operations

**Use when**:
- Running single, independent commands
- Maximum isolation is needed
- Commands don't depend on previous state

#### shell Mode (Stateful)

Commands run in persistent shell session:

```yaml
hosts:
  - name: stateful-server
    execution_mode: "shell"
```

**Characteristics**:
- Working directory persists across commands
- Environment variables persist
- Shell history available
- Supports complex shell operations
- Sessions maintain state

**Use when**:
- Running multiple related commands
- Working directory needs to persist
- Setting environment variables
- Complex shell operations required

### Authentication Methods

#### SSH Key Authentication (Recommended)

```yaml
hosts:
  - name: key-auth-server
    host: "example.com"
    username: "user"
    private_key_path: "~/.ssh/id_rsa"
    # Optional: passphrase for encrypted key
    # passphrase: "key-passphrase"
```

#### Password Authentication (Not Recommended)

```yaml
hosts:
  - name: password-server
    host: "example.com"
    username: "user"
    password: "secret-password"
```

**Security Warning**: Avoid storing passwords in configuration files. Use SSH keys instead.

### Multiple Hosts Example

```yaml
hosts:
  - name: web-proxy
    description: "Nginx reverse proxy server"
    host: "proxy.example.com"
    username: "webadmin"
    private_key_path: "~/.ssh/proxy_key"
    execution_mode: "shell"

  - name: app-server
    description: "Python application server"
    host: "app.example.com"
    username: "appuser"
    private_key_path: "~/.ssh/app_key"
    execution_mode: "shell"

  - name: db-server
    description: "PostgreSQL database server"
    host: "db.example.com"
    username: "dbadmin"
    private_key_path: "~/.ssh/db_key"
    execution_mode: "exec"

  - name: cache-server
    description: "Redis caching server"
    host: "cache.example.com"
    username: "cacheadmin"
    private_key_path: "~/.ssh/cache_key"
    execution_mode: "exec"
```

## Session Management Configuration

The `session` section controls SSH session lifecycle and resource limits.

```yaml
session:
  idle_timeout: 30
  max_sessions_per_host: 5
  cleanup_interval: 60
```

### Session Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `idle_timeout` | integer | `30` | Minutes before closing idle sessions |
| `max_sessions_per_host` | integer | `5` | Maximum concurrent sessions per host |
| `cleanup_interval` | integer | `60` | Seconds between cleanup checks |

### Session Behavior

**Idle Timeout**: Sessions are automatically closed after the specified idle time:
```yaml
session:
  idle_timeout: 30  # Close after 30 minutes of inactivity
```

**Session Limits**: Prevents resource exhaustion:
```yaml
session:
  max_sessions_per_host: 5  # Maximum 5 concurrent sessions per host
```

**Cleanup Interval**: How often to check for idle sessions:
```yaml
session:
  cleanup_interval: 60  # Check every 60 seconds
```

## Logging Configuration

### Log Levels

```yaml
server:
  log_level: "INFO"  # DEBUG, INFO, WARN, ERROR
```

- **DEBUG**: Detailed debugging information
- **INFO**: General informational messages
- **WARN**: Warning messages
- **ERROR**: Error messages only

### Log Output

Logs are written to:
- **STDERR** for console output
- **logs/ssh_mcp_bridge.log** (if file logging is enabled)

## Environment Variables

Configuration values can be overridden using environment variables:

```bash
# Server configuration
export SSH_MCP_HOST=0.0.0.0
export SSH_MCP_PORT=8080
export SSH_MCP_LOG_LEVEL=DEBUG

# OAuth configuration
export AUTH_MODE=oidc
export IDP_ISSUER=https://auth.example.com/
export IDP_AUDIENCE=https://api.example.com
export IDP_JWKS_URI=https://auth.example.com/.well-known/jwks.json

# API key (for non-OAuth HTTP mode)
export SSH_MCP_API_KEY=your-secret-key
```

## Configuration Validation

SSH MCP Bridge validates configuration on startup:

```bash
# Test configuration
python -m ssh_mcp_bridge --validate config.yaml

# Run with debug logging to see validation details
python -m ssh_mcp_bridge --log-level DEBUG config.yaml
```

Common validation errors:
- Missing required fields (name, host, username)
- Invalid execution_mode (must be "exec" or "shell")
- Missing authentication (no private_key_path or password)
- Invalid port numbers
- Duplicate host names

## Complete Configuration Example

```yaml
# Server configuration
server:
  host: "0.0.0.0"
  port: 8080
  enable_http: true
  enable_stdio: false
  
  # OAuth authentication
  oauth:
    enabled: true
    issuer: "https://auth.example.com/"
    audience: "https://ssh-mcp.example.com"
    jwks_uri: "https://auth.example.com/.well-known/jwks.json"
  
  # CORS configuration
  cors_origins:
    - "https://chat.openai.com"
    - "https://chatgpt.com"
  
  log_level: "INFO"

# SSH hosts
hosts:
  - name: web-proxy
    description: "Nginx reverse proxy handling SSL termination"
    host: "10.0.1.10"
    port: 22
    username: "nginx-admin"
    private_key_path: "~/.ssh/proxy_key"
    execution_mode: "shell"
    disable_pager: true

  - name: k8s-master
    description: "Kubernetes master node"
    host: "10.0.1.20"
    port: 22
    username: "k8s-admin"
    private_key_path: "~/.ssh/k8s_key"
    execution_mode: "shell"
    disable_pager: true

  - name: postgres-db
    description: "PostgreSQL database primary"
    host: "10.0.1.30"
    port: 22
    username: "postgres"
    private_key_path: "~/.ssh/db_key"
    execution_mode: "exec"
    disable_pager: true

  - name: redis-cache
    description: "Redis caching layer"
    host: "10.0.1.40"
    port: 22
    username: "redis-admin"
    private_key_path: "~/.ssh/cache_key"
    execution_mode: "exec"
    disable_pager: true

# Session management
session:
  idle_timeout: 30
  max_sessions_per_host: 5
  cleanup_interval: 60
```

## Security Best Practices

1. **File Permissions**: Restrict config file access
   ```bash
   chmod 600 config.yaml
   ```

2. **SSH Keys**: Use key-based authentication
   ```bash
   chmod 600 ~/.ssh/id_rsa
   ```

3. **API Keys**: Generate strong keys
   ```bash
   openssl rand -hex 32
   ```

4. **OAuth**: Use OAuth for production HTTP deployments

5. **Secrets Management**: Consider using environment variables or secret management tools instead of storing secrets in config files

6. **Minimal Permissions**: Use SSH users with minimal required permissions

7. **Audit Logging**: Enable detailed logging for compliance

## Next Steps

- Review [Security Best Practices](SECURITY.md)
- Set up [OAuth Authentication](CHATGPT_INTEGRATION.md)
- Learn about [Docker Deployment](DOCKER.md)
- Understand [Architecture](ARCHITECTURE.md)
