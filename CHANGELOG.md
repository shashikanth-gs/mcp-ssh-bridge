# Changelog

All notable changes to SSH MCP Bridge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned Features
- File transfer support (SCP/SFTP)
- Multi-hop SSH (bastion/jump hosts)
- Resource definitions for server state
- Prompt templates for common operations
- WebSocket support for real-time streaming
- Prometheus metrics export

## [2.0.0] - 2025-12-31

### Added
- Complete rewrite using FastMCP framework
- Dual transport support (STDIO and HTTP/SSE)
- OAuth 2.0 / OIDC authentication for HTTP mode
- JWT token validation with JWKS support
- OAuth discovery endpoint for ChatGPT integration
- Session statistics and monitoring
- Health check endpoint
- User identity tracking in audit logs
- Comprehensive documentation suite
- Docker deployment support
- Multiple configuration examples
- Session management with automatic cleanup

### Features
- **STDIO Mode**: Integration with Claude Desktop, VS Code
- **HTTP Mode**: Integration with ChatGPT and web clients
- **Multi-server orchestration**: Manage unlimited SSH hosts
- **Credential isolation**: AI agents never see IPs, passwords, or keys
- **Self-discovery**: Servers advertise capabilities to agents
- **Auditability**: Complete command logging with user context
- **Security**: OAuth, API keys, session timeout, resource limits
- **Scalability**: Session pooling, automatic cleanup, horizontal scaling

### Documentation
- Quick Start Guide
- Installation Guide
- Configuration Reference
- Docker Deployment Guide
- ChatGPT Integration Guide
- Security Best Practices
- Architecture Overview
- Contributing Guidelines

### Security
- Non-root container execution
- Read-only volume mounts
- JWT signature verification (RS256)
- Issuer and audience validation
- Automatic session timeout
- Resource limits per host

### Technical
- Python 3.9+ support
- FastMCP 2.11.3 integration
- Paramiko for SSH protocol
- FastAPI for HTTP API
- Uvicorn ASGI server
- PyJWT for token validation
- Type hints throughout
- Comprehensive test coverage

## [1.0.0] - 2024 (Legacy Version)

### Initial Release
- Custom MCP protocol implementation
- HTTP transport only
- API key authentication
- Basic SSH session management
- Manual tool schema definitions
- FastAPI + Uvicorn stack

### Limitations
- No STDIO support
- Custom protocol handling required
- Manual schema maintenance
- Limited scalability
- No OAuth support

---

## Migration Guide: v1 to v2

### Breaking Changes

1. **Configuration Format**: Updated YAML structure with `server` section
2. **Dependencies**: Now requires FastMCP instead of custom MCP implementation
3. **Tool Names**: Some tools renamed for consistency
4. **Authentication**: Enhanced OAuth support, API key format unchanged

### Migration Steps

1. **Update configuration file**:
   ```yaml
   # v1
   hosts:
     - name: server
   
   # v2
   server:
     enable_http: true
   hosts:
     - name: server
   ```

2. **Update dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Update client integration** (if using custom client):
   - FastMCP now handles protocol
   - Tool schemas auto-generated
   - See documentation for updated endpoints

4. **Test thoroughly** before production deployment

### New Features Available

- STDIO mode for local MCP clients
- OAuth 2.0 authentication
- Session statistics
- Enhanced logging and audit trails
- Docker deployment
- Comprehensive documentation

---

## Version History

- **v2.0.0** (2025-12-31): Complete rewrite with FastMCP, dual transport, OAuth support
- **v1.0.0** (2024): Initial release with HTTP-only custom MCP implementation

---

## Support

For questions, issues, or feature requests:
- **GitHub Issues**: https://github.com/shashikanth-gs/mcp-ssh-bridge/issues
- **Discussions**: https://github.com/shashikanth-gs/mcp-ssh-bridge/discussions
- **Documentation**: https://github.com/shashikanth-gs/mcp-ssh-bridge/tree/main/docs
