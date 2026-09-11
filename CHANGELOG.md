# Changelog

All notable changes to SSH MCP Bridge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned Features
- Multi-hop SSH (bastion/jump hosts)
- Resource definitions for server state
- Prompt templates for common operations
- WebSocket support for real-time streaming
- Prometheus metrics export

## [2.2.0] - 2026-09-11

### Security
- Protect both the MCP endpoint and the REST compatibility routes with one
  framework-native authentication policy instead of two divergent checks.
  Configured API keys previously protected only the REST routes; `/mcp` could
  be reached without authentication whenever OAuth was not configured.
- Add `StaticTokenVerifier` (API key), `JWTVerifier`/`RemoteAuthProvider`
  (JWT/JWKS with RFC 9728 protected-resource metadata), `Auth0Provider`
  (interactive OAuth), and `MultiAuth` (mixed-mode migration) via explicit
  `auth_mode: auto|none|api_key|oidc`. Invalid explicit configuration now
  fails startup instead of silently exposing an anonymous service.
- Change the default HTTP bind from `0.0.0.0` to `127.0.0.1`; a non-loopback
  bind now requires an explicit `allowed_hosts` list and rejects `*`.
- Validate the `Host` and browser `Origin` headers before MCP dispatch to
  mitigate DNS rebinding; reject wildcard CORS origins for non-loopback binds.
- Rate-limit requests per authenticated client identity, applied consistently
  to both `/mcp` and the `/api/v1/*` REST routes (the REST routes previously
  had no rate limit at all).
- Reject globally shared, process-wide persistent shell sessions (
  `execution_mode: shell`) in HTTP mode by default; require an explicit
  `allow_shared_shell_sessions: true` opt-in for single-principal deployments.
- Stop returning or logging the submitted command text in `execute_command`
  results, in either `exec` or `shell` execution mode.
- Mask unexpected MCP and REST error details from clients, while still
  surfacing expected, safe-to-show conditions (unknown host, a path-policy
  violation, a dropped SSH connection, a command timeout) with their real
  message rather than a generic error — see Fixed below.

### Changed
- Move the remote MCP transport from legacy HTTP+SSE to stateless MCP
  Streamable HTTP at `/mcp`.
- `execute_command` now returns a typed `CommandResult` with `host`, `output`,
  `success`, and an always-present `exit_status` (previously omitted on
  success). The `command` field is no longer included in the response.
- Persistent shell-mode command results now report the command's real exit
  status, captured via a unique per-call marker, instead of always reporting
  success.

### Added
- GitHub Actions CI running the test suite on Python 3.10-3.13 and checking
  `black`/`isort` formatting on every pull request and push to `main`. There
  was previously no automated status check on this repository.
- Regression coverage for authentication modes, HTTP Host/Origin/CORS
  handling, rate limiting, error masking, and typed command results.

### Fixed
- `mask_error_details=True` was masking every tool exception in HTTP mode,
  including ordinary expected ones. An agent hitting a typo'd host name, a
  path-policy violation, a dropped SSH connection, or a command timeout over
  `/mcp` previously got only an opaque `"Error calling tool"` message with no
  indication of why, while the equivalent REST call already returned the real
  message. These are now re-raised as FastMCP `ToolError`s, which bypass
  masking, so `/mcp` and REST behave consistently. Only genuinely unexpected
  exceptions are still masked.
- The `/api/v1/*` REST compatibility routes had no rate limit at all, so an
  authenticated client could bypass the `/mcp` rate limit entirely by calling
  REST instead. They now enforce the same `rate_limit_per_minute` budget,
  via a separate limiter tracked independently from FastMCP's own `/mcp`
  limiter (see [CONFIGURATION.md](docs/CONFIGURATION.md#rate-limiting)).

### Compatibility Notes
This release contains changes that existing clients may need to adjust for,
even though it ships as a minor version:
- `execute_command` responses no longer include a `command` field.
- `execute_command.exit_status` is now always present (previously present
  only on failure).
- Legacy HTTP+SSE clients must move to Streamable HTTP.
- HTTP mode binds to loopback by default; a remote bind now requires
  `allowed_hosts` and, in most cases, explicit authentication.
- JWT/JWKS mode requires an externally visible HTTPS `oauth.base_url` (or
  `BASE_URL`) so RFC 9728 metadata can be generated.
- Remote wildcard CORS (`cors_origins: ["*"]`) is rejected for non-loopback
  binds.
- HTTP hosts configured with `execution_mode: shell` must move to `exec`, or
  the deployment must explicitly set `allow_shared_shell_sessions: true`.

## [2.1.0] - 2026-09-02

### Added
- Bidirectional SFTP file transfers with `upload_file` and `download_file` MCP tools.
- Remote file inspection tools: `stat_remote_path` and `list_remote_directory`.
- File-transfer policy discovery with `get_file_transfer_config`.
- REST endpoints for server-side upload, download, remote stat, and remote directory listing in HTTP mode.
- Dedicated file-transfer guide covering STDIO and HTTP deployment semantics.
- Release note at `docs/releases/2.1.0.md`.
- Configurable file-transfer safety policy:
  - `allowed_local_paths`
  - `allowed_remote_write_paths`
  - `max_file_transfer_mb`
- Unit tests for transfer policy and security config parsing.
- Documentation for STDIO versus HTTP file-transfer path semantics.

### Changed
- Upgraded runtime dependency support to FastMCP 4.0.1 and MCP SDK 2.1.1.
- Raised the Python requirement to 3.10+ to match FastMCP 4.
- The HTTP API and app version are now aligned at `2.1.0`.
- Config examples include explicit file-transfer policy blocks.
- README, Quick Start, Docker, and ChatGPT integration docs describe SFTP transfer support.

### Security
- Local upload sources and download destinations are restricted to configured server-local paths.
- Remote upload destinations are restricted to configured remote write paths.
- Private local runtime config files are ignored by Git.

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

- **v2.2.0** (2026-09-11): Framework-native HTTP authentication, Streamable HTTP transport, typed command results, and consistent rate limiting/error handling
- **v2.1.0** (2026-09-02): Added bidirectional SFTP transfer tools and transfer safety policy
- **v2.0.0** (2025-12-31): Complete rewrite with FastMCP, dual transport, OAuth support
- **v1.0.0** (2024): Initial release with HTTP-only custom MCP implementation

---

## Support

For questions, issues, or feature requests:
- **GitHub Issues**: https://github.com/shashikanth-gs/mcp-ssh-bridge/issues
- **Discussions**: https://github.com/shashikanth-gs/mcp-ssh-bridge/discussions
- **Documentation**: https://github.com/shashikanth-gs/mcp-ssh-bridge/tree/main/docs
