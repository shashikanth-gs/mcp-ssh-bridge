# Architecture Overview

Technical architecture documentation for SSH MCP Bridge.

## System Architecture

SSH MCP Bridge uses a layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                          │
│  Claude Desktop | VS Code | ChatGPT | Custom MCP Clients│
└──────────────┬──────────────────────────┬────────────────┘
               │                          │
               v (STDIO)                  v (HTTP/SSE)
┌─────────────────────────────────────────────────────────┐
│                    API LAYER                            │
│  ┌──────────────────┐    ┌──────────────────┐          │
│  │  mcp_server.py   │    │  http_server.py  │          │
│  │  (FastMCP/STDIO) │    │  (FastAPI/HTTP)  │          │
│  └────────┬─────────┘    └────────┬─────────┘          │
└───────────┼──────────────────────┼────────────────────────┘
            │                      │
            v                      v
┌─────────────────────────────────────────────────────────┐
│                 SERVICE LAYER                           │
│           ┌─────────────────────────┐                   │
│           │   mcp_service.py        │                   │
│           │  (Business Logic)       │                   │
│           └──────────┬──────────────┘                   │
└──────────────────────┼──────────────────────────────────┘
                       │
                       v
┌─────────────────────────────────────────────────────────┐
│                  CORE LAYER                             │
│  ┌──────────────────┐    ┌──────────────────┐          │
│  │ session_manager  │───▶│  ssh_session.py  │          │
│  │      .py         │    │  (SSH Protocol)  │          │
│  └──────────────────┘    └──────────────────┘          │
└─────────────────────────────────────────────────────────┘
                       │
                       v
┌─────────────────────────────────────────────────────────┐
│               SSH SERVERS                               │
│  Web Server | App Server | DB Server | Cache | etc.    │
└─────────────────────────────────────────────────────────┘
```

## Component Breakdown

### Client Layer

**MCP Clients** that connect to SSH MCP Bridge:

**STDIO Mode**:
- Claude Desktop
- VS Code with MCP extension
- Any local MCP client

**HTTP Mode**:
- ChatGPT
- Custom web applications
- Enterprise integrations
- Remote MCP clients

### API Layer

#### mcp_server.py (FastMCP STDIO)

**Responsibilities**:
- Handle STDIO transport (JSON-RPC via stdin/stdout)
- Implement MCP protocol using FastMCP framework
- Define MCP tools with decorators
- Route requests to service layer

**Key Features**:
- Automatic protocol handling
- Schema generation from type hints
- Simple decorator-based tool definition

**Example**:
```python
@mcp.tool()
def list_hosts() -> list[dict]:
    """List all available SSH hosts."""
    return service.list_hosts()
```

#### http_server.py (FastAPI HTTP)

**Responsibilities**:
- Handle HTTP/SSE transport
- Implement REST API endpoints
- Authentication (API key or OAuth)
- CORS management
- OpenAPI documentation

**Key Features**:
- OAuth 2.0 / OIDC support
- JWT token validation
- Health check endpoints
- Session statistics API
- OAuth discovery endpoint

**Endpoints**:
- `GET /health` - Health check
- `GET /.well-known/oauth-protected-resource` - OAuth discovery
- `GET /api/v1/hosts` - List SSH hosts
- `POST /api/v1/execute` - Execute command
- `GET /api/v1/stats` - Session statistics
- `POST /api/v1/close-session` - Close session

### Service Layer

#### mcp_service.py

**Responsibilities**:
- Business logic orchestration
- Input validation
- Error handling
- Logging and audit trails
- Session statistics

**Key Operations**:
- `list_hosts()` - Return available SSH hosts
- `execute_command(host, command)` - Execute SSH command
- `get_working_directory(host)` - Get current directory
- `close_session(host)` - Close SSH session
- `get_session_stats()` - Get session statistics

**Benefits**:
- Single source of truth for business logic
- Shared by both STDIO and HTTP transports
- Easy to test and maintain
- Consistent behavior across transports

### Core Layer

#### session_manager.py

**Responsibilities**:
- Manage pool of SSH sessions
- Session lifecycle management
- Automatic cleanup of idle sessions
- Connection pooling and reuse
- Resource limits enforcement

**Key Features**:
- Session pooling per host
- Automatic idle timeout
- Configurable max sessions per host
- Periodic cleanup of expired sessions
- Thread-safe operation

**Session Lifecycle**:
```
1. Client requests command execution
2. Session Manager checks for existing session
3. If not exists, create new SSHSession
4. If exists and not idle, reuse session
5. Execute command via session
6. Update last activity timestamp
7. Background cleanup removes idle sessions
```

#### ssh_session.py

**Responsibilities**:
- Individual SSH connection wrapper
- Command execution (exec vs shell mode)
- Working directory tracking
- Pager handling
- Output capture and formatting

**Execution Modes**:

**exec mode** (stateless):
- Each command runs independently
- No working directory persistence
- No environment variable persistence
- Safer for untrusted operations

**shell mode** (stateful):
- Persistent shell session
- Working directory maintained
- Environment variables persist
- Supports complex shell operations

**Features**:
- Automatic pager disabling (for less, more, etc.)
- UTF-8 output handling
- Error capture and reporting
- Connection keepalive

### Models Layer

#### config.py

**Responsibilities**:
- Configuration data models
- YAML parsing and validation
- Environment variable override
- Default value management

**Models**:
- `ServerConfig` - Server settings (host, port, auth, etc.)
- `HostConfig` - SSH host configuration
- `SessionConfig` - Session management settings
- `OAuthConfig` - OAuth/OIDC settings

### Utils Layer

#### logging.py

**Responsibilities**:
- Logging configuration
- Log format standardization
- Handler management

#### jwt_verifier.py

**Responsibilities**:
- JWT token validation
- JWKS fetching and caching
- Signature verification (RS256)
- Claims extraction

## Data Flow

### STDIO Mode Flow

```
1. Claude Desktop sends JSON-RPC request via STDIN
   {
     "jsonrpc": "2.0",
     "method": "tools/call",
     "params": {
       "name": "execute_command",
       "arguments": {"host": "web-server", "command": "uptime"}
     }
   }

2. FastMCP parses and routes to mcp_server.py

3. execute_command() tool function calls service layer
   service.execute_command("web-server", "uptime")

4. Service layer calls session manager
   session_manager.execute_command("web-server", "uptime")

5. Session manager gets or creates SSH session
   session = sessions["web-server"] or create_new_session()

6. SSH session executes command via Paramiko
   output = session.execute("uptime")

7. Results bubble back up through layers

8. FastMCP formats JSON-RPC response to STDOUT
   {
     "jsonrpc": "2.0",
     "result": {
       "host": "web-server",
       "command": "uptime",
       "output": "10:30:45 up 15 days...",
       "success": true
     }
   }
```

### HTTP Mode Flow

```
1. ChatGPT sends HTTP request with OAuth token
   POST /api/v1/execute
   Authorization: Bearer eyJhbGc...
   Content-Type: application/json
   
   {
     "host": "web-server",
     "command": "uptime"
   }

2. FastAPI middleware validates JWT token
   - Verify signature using JWKS
   - Check issuer and audience
   - Validate expiration
   - Extract user claims

3. HTTP server routes to endpoint handler
   @app.post("/api/v1/execute")
   async def execute_command(request: ExecuteRequest)

4. Handler calls service layer
   result = service.execute_command(request.host, request.command)

5. Service layer calls session manager (same as STDIO)

6. Results return through layers

7. FastAPI formats HTTP response
   {
     "host": "web-server",
     "command": "uptime",
     "output": "10:30:45 up 15 days...",
     "success": true,
     "user": "user@example.com"
   }
```

## Security Architecture

### Defense in Depth

**Layer 1: Transport Security**
- HTTPS for HTTP mode
- API key or OAuth authentication
- CORS restrictions

**Layer 2: Credential Isolation**
- SSH credentials stored server-side only
- Clients only see friendly host names
- No IP addresses exposed to AI

**Layer 3: Session Management**
- Automatic session timeout
- Resource limits per host
- Session cleanup

**Layer 4: SSH Security**
- Key-based authentication preferred
- Per-host SSH users
- Minimal permissions

**Layer 5: Audit Logging**
- All commands logged
- User identity tracked
- Timestamp and result captured

### OAuth Authentication Flow

```
1. Client discovers OAuth metadata
   GET /.well-known/oauth-protected-resource
   
   Response:
   {
     "authorization_servers": ["https://auth.example.com/"],
     "resource": "https://ssh-mcp.example.com",
     "scopes_supported": ["openid", "profile", "email", "mcp:execute"]
   }

2. Client redirects user to OAuth provider
   https://auth.example.com/authorize?
     client_id=...&
     redirect_uri=...&
     scope=openid+profile+email+mcp:execute

3. User authenticates and authorizes

4. OAuth provider issues authorization code

5. Client exchanges code for JWT token
   POST https://auth.example.com/oauth/token
   
   Response:
   {
     "access_token": "eyJhbGc...",
     "token_type": "Bearer",
     "expires_in": 86400
   }

6. Client uses JWT in API requests
   Authorization: Bearer eyJhbGc...

7. SSH MCP Bridge validates JWT
   - Fetch JWKS from OAuth provider
   - Verify signature (RS256)
   - Check issuer, audience, expiration
   - Extract user claims (email, name, etc.)

8. Command execution proceeds with user context
```

## Session Management

### Session Pooling

**Purpose**: Reuse SSH connections to avoid connection overhead

**Implementation**:
```python
sessions: Dict[str, SSHSession] = {}

def get_or_create_session(host_name: str) -> SSHSession:
    if host_name in sessions:
        session = sessions[host_name]
        if not session.is_idle():
            return session
        else:
            session.close()
    
    session = SSHSession(host_config)
    sessions[host_name] = session
    return session
```

### Automatic Cleanup

**Purpose**: Remove idle sessions to free resources

**Implementation**:
- Background thread runs every `cleanup_interval` seconds
- Checks all sessions for last activity time
- Closes sessions idle longer than `idle_timeout`
- Removes closed sessions from pool

**Configuration**:
```yaml
session:
  idle_timeout: 30        # Minutes
  cleanup_interval: 60    # Seconds
  max_sessions_per_host: 5
```

## Scalability Considerations

### Horizontal Scaling

**Stateless HTTP Mode**:
- Deploy multiple instances behind load balancer
- Each instance maintains its own session pool
- No shared state between instances

**Considerations**:
- Use sticky sessions for shell mode
- Session affinity based on user or host
- Future: Redis for shared session metadata

### Vertical Scaling

**Resource Limits**:
- `max_sessions_per_host` prevents resource exhaustion
- Container resource limits (CPU, memory)
- Connection pooling reduces overhead

**Performance Optimizations**:
- Connection reuse via session pooling
- Async operations in FastAPI
- Lazy session creation
- Efficient cleanup

### Load Balancing

**For HTTP Mode**:
```
                  Load Balancer
                        |
          +-------------+-------------+
          |             |             |
    Instance 1    Instance 2    Instance 3
          |             |             |
          +-------------+-------------+
                        |
                  SSH Servers
```

**Recommended**: Use sticky sessions or consistent hashing

## Extension Points

### Adding New MCP Tools

1. Add method to `McpService` class
2. Decorate with `@mcp.tool()` in mcp_server.py
3. Add HTTP endpoint in http_server.py (optional)

### Adding New Transport

1. Create new module in `api/` directory
2. Implement transport-specific protocol
3. Use existing service layer for business logic
4. Add mode selection in app.py

### Adding Authentication Methods

1. Extend http_server.py with new auth middleware
2. Update config.py with new auth settings
3. Document in configuration reference

## Technology Stack

### Core Dependencies

- **Python 3.9+**: Runtime environment
- **FastMCP**: MCP protocol framework
- **Paramiko**: SSH protocol implementation
- **FastAPI**: HTTP API framework
- **Uvicorn**: ASGI server
- **PyYAML**: Configuration parsing
- **PyJWT**: JWT token validation
- **cryptography**: Cryptographic operations

### Why These Technologies?

**FastMCP**:
- Official MCP framework for Python
- Automatic protocol handling
- Decorator-based API
- Active development

**Paramiko**:
- Pure Python SSH implementation
- Stable and well-tested
- Supports all SSH features

**FastAPI**:
- Modern async Python framework
- Automatic OpenAPI documentation
- High performance
- Type hints and validation

## Testing Strategy

### Unit Tests

- Test each layer independently
- Mock dependencies
- Fast execution

### Integration Tests

- Test layer interactions
- Use test fixtures
- Real SSH connections (test servers)

### End-to-End Tests

- Full stack testing
- Both STDIO and HTTP modes
- Docker-based testing

## Monitoring and Observability

### Metrics

- Active sessions per host
- Command execution count
- Command execution duration
- Authentication success/failure rate
- Error rate by type

### Logging

- Structured logging (JSON format)
- Configurable log levels
- Per-component loggers
- Audit trail for commands

### Health Checks

- `/health` endpoint
- Service status
- Connection status
- Resource utilization

## Future Enhancements

### Planned Features

- **File Transfer**: SCP/SFTP support for file operations
- **Multi-Hop SSH**: Bastion/jump host support
- **Resource Definitions**: Expose server state as MCP resources
- **Prompt Templates**: Pre-defined command patterns
- **Session Persistence**: Save and restore sessions across restarts
- **Metrics Export**: Prometheus endpoint
- **WebSocket Support**: Real-time command streaming
- **Multi-User**: User-specific credentials and permissions

### Architecture Evolution

- **Service Mesh**: Istio/Linkerd integration for microservices
- **Event-Driven**: Message queue integration (RabbitMQ, Kafka)
- **CQRS**: Separate read/write models
- **Cache Layer**: Redis for session metadata and caching
- **GraphQL**: Alternative API interface

## Performance Benchmarks

### Typical Performance

- **Command Execution**: 50-200ms (depending on SSH latency)
- **Session Creation**: 500-1000ms (initial SSH handshake)
- **Session Reuse**: 10-50ms overhead
- **HTTP Request**: 100-300ms total (including validation)

### Optimization Tips

- Use shell mode for related commands
- Enable session pooling
- Tune idle_timeout for your workload
- Deploy close to SSH servers (reduce latency)
- Use HTTP/2 for better performance

## Conclusion

SSH MCP Bridge's layered architecture provides:

- **Flexibility**: Support multiple transports and auth methods
- **Scalability**: Horizontal and vertical scaling options
- **Security**: Defense in depth with multiple security layers
- **Maintainability**: Clear separation of concerns
- **Extensibility**: Easy to add new features and integrations

## Next Steps

- Review [Configuration Reference](CONFIGURATION.md)
- Learn about [Security Best Practices](SECURITY.md)
- Set up [Docker Deployment](DOCKER.md)
- Configure [OAuth Integration](CHATGPT_INTEGRATION.md)
