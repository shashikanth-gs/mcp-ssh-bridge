"""HTTP server implementation with FastMCP authentication."""

import ipaddress
import logging
import os
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastmcp.server.auth import MultiAuth, RemoteAuthProvider
from fastmcp.server.auth.providers.jwt import JWTVerifier, StaticTokenVerifier
from pydantic import BaseModel

from ssh_mcp_bridge.api.mcp_server import create_mcp_server
from ssh_mcp_bridge.api.rate_limiter import SlidingWindowRateLimiter
from ssh_mcp_bridge.models.config import ServerConfig
from ssh_mcp_bridge.services.mcp_service import McpService

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


def _internal_server_error(operation: str, error: Exception) -> HTTPException:
    """Log non-sensitive failure metadata and return a generic HTTP error."""
    logger.error("%s failed (%s)", operation, type(error).__name__)
    return HTTPException(status_code=500, detail="Internal server error")


class ExecuteCommandRequest(BaseModel):
    """Request model for execute_command."""

    host: str
    command: str


class GetWorkingDirectoryRequest(BaseModel):
    """Request model for get_working_directory."""

    host: str


class RemotePathRequest(BaseModel):
    """Request model for remote path operations."""

    host: str
    remote_path: str


class ListRemoteDirectoryRequest(BaseModel):
    """Request model for list_remote_directory."""

    host: str
    remote_path: str
    limit: int = 200


class DownloadFileRequest(BaseModel):
    """Request model for download_file."""

    host: str
    remote_path: str
    local_path: str
    overwrite: bool = False


class UploadFileRequest(BaseModel):
    """Request model for upload_file."""

    host: str
    local_path: str
    remote_path: str
    overwrite: bool = False


class CloseSessionRequest(BaseModel):
    """Request model for close_session."""

    host: str


def create_fastmcp_auth(server_config: ServerConfig):
    """Build one FastMCP auth provider for every enabled bearer-token source.

    Static API keys are retained for backward compatibility. FastMCP documents
    ``StaticTokenVerifier`` as a development/internal-use mechanism; remote
    production deployments should use JWT/JWKS or Auth0 instead.

    Invalid explicit authentication configuration raises ``ValueError`` so an
    HTTP server can never silently fall back to anonymous access.
    """
    mode = server_config.auth_mode
    oauth = server_config.oauth
    use_api_key = mode in {"auto", "api_key"} and bool(server_config.api_key)
    use_oidc = mode in {"auto", "oidc"} and bool(oauth and oauth.enabled)

    if mode == "api_key" and not server_config.api_key:
        raise ValueError("auth_mode=api_key requires api_key or API_KEY")
    if mode == "oidc" and not use_oidc:
        raise ValueError("auth_mode=oidc requires oauth.enabled=true")
    if mode == "none":
        return None

    static_verifier = None
    if use_api_key:
        static_verifier = StaticTokenVerifier(
            tokens={
                server_config.api_key: {
                    "client_id": "configured-api-key",
                    "scopes": ["ssh:access"],
                }
            },
            required_scopes=["ssh:access"],
        )
        logger.warning(
            "Static API-key authentication is enabled; use JWT/JWKS or Auth0 "
            "for production deployments"
        )

    oidc_provider = None
    if use_oidc:
        if not oauth.issuer or not oauth.audience:
            raise ValueError("OAuth requires issuer and audience")

        if oauth.provider == "jwt":
            if not oauth.jwks_uri:
                raise ValueError("oauth.provider=jwt requires jwks_uri")
            if not oauth.base_url:
                raise ValueError("oauth.provider=jwt requires oauth.base_url or BASE_URL")
            jwt_verifier = JWTVerifier(
                jwks_uri=oauth.jwks_uri,
                issuer=oauth.issuer.rstrip("/"),
                audience=oauth.audience,
                required_scopes=oauth.required_scopes or None,
                ssrf_safe=True,
            )
            oidc_provider = RemoteAuthProvider(
                token_verifier=jwt_verifier,
                authorization_servers=[oauth.issuer],
                base_url=oauth.base_url,
                scopes_supported=oauth.required_scopes or None,
                resource_name="SSH MCP Bridge",
            )
        else:
            from fastmcp.server.auth.providers.auth0 import Auth0Provider

            client_id = os.environ.get("AUTH0_CLIENT_ID")
            client_secret = os.environ.get("AUTH0_CLIENT_SECRET")
            if not client_id or not client_secret or not oauth.base_url:
                raise ValueError(
                    "oauth.provider=auth0 requires AUTH0_CLIENT_ID, "
                    "AUTH0_CLIENT_SECRET, and oauth.base_url or BASE_URL"
                )

            jwt_signing_key = os.environ.get("JWT_SIGNING_KEY")
            if not jwt_signing_key:
                logger.warning(
                    "JWT_SIGNING_KEY is not set; configure an explicit signing key "
                    "and persistent encrypted client storage for multi-instance production"
                )

            oidc_provider = Auth0Provider(
                config_url=f"{oauth.issuer.rstrip('/')}/.well-known/openid-configuration",
                client_id=client_id,
                client_secret=client_secret,
                audience=oauth.audience,
                base_url=oauth.base_url,
                required_scopes=oauth.required_scopes or ["openid"],
                jwt_signing_key=jwt_signing_key,
            )

    if oidc_provider and static_verifier:
        return MultiAuth(server=oidc_provider, verifiers=[static_verifier])
    return oidc_provider or static_verifier


def _is_loopback_host(host: str) -> bool:
    """Return whether a bind host is explicitly loopback-only."""
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _validate_http_security(
    service: McpService,
    server_config: ServerConfig,
    auth,
) -> None:
    """Reject unsafe HTTP configurations before the listening socket opens."""
    is_loopback = _is_loopback_host(server_config.host)
    if auth is None and not is_loopback and not server_config.allow_unauthenticated_http:
        raise ValueError(
            "Unauthenticated HTTP may only bind to loopback. Configure authentication "
            "or explicitly set allow_unauthenticated_http=true."
        )

    if not is_loopback and not server_config.allowed_hosts:
        raise ValueError("Non-loopback HTTP requires an explicit allowed_hosts list")
    if "*" in server_config.allowed_hosts:
        raise ValueError("allowed_hosts must not contain '*' in HTTP mode")
    if not is_loopback and "*" in server_config.cors_origins:
        raise ValueError("cors_origins must not contain '*' for non-loopback HTTP")

    hosts = service.session_manager.config.hosts
    shared_shell_hosts = [host.name for host in hosts if host.execution_mode == "shell"]
    if shared_shell_hosts and not server_config.allow_shared_shell_sessions:
        joined = ", ".join(shared_shell_hosts)
        raise ValueError(
            "HTTP mode cannot use globally shared shell sessions by default. "
            f"Use execution_mode=exec for: {joined}. If this is an intentionally "
            "single-principal deployment, set allow_shared_shell_sessions=true."
        )


def create_http_server(
    service: McpService,
    server_config: ServerConfig,
) -> FastAPI:
    """Create and configure FastAPI HTTP server.

    Args:
        service: MCP service instance
        server_config: Server configuration

    Returns:
        Configured FastAPI application
    """
    # Build authentication once, then use the same provider for MCP and REST.
    fastmcp_auth = create_fastmcp_auth(server_config)
    _validate_http_security(service, server_config, fastmcp_auth)

    mcp_server = create_mcp_server(
        service,
        "SSH Bridge",
        auth=fastmcp_auth,
        mask_error_details=True,
        rate_limit_per_minute=server_config.rate_limit_per_minute,
    )
    mcp_http_app = mcp_server.http_app(
        path="/mcp",
        transport="http",
        stateless_http=True,
        host_origin_protection=True,
        allowed_hosts=server_config.allowed_hosts,
        allowed_origins=server_config.cors_origins,
    )

    # FastMCP's lifespan initializes the Streamable HTTP task group. The parent
    # ASGI app must own it when the FastMCP app is mounted.
    app = FastAPI(
        title="SSH MCP Bridge API",
        description="HTTP API for SSH MCP Bridge",
        version="2.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=mcp_http_app.lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=server_config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # REST compatibility endpoints validate through the same provider as MCP,
    # and are rate-limited with the same per-client budget FastMCP applies to
    # /mcp so the REST routes cannot be used to bypass it.
    rest_rate_limiter = SlidingWindowRateLimiter(max_requests=server_config.rate_limit_per_minute)

    async def verify_authentication(
        credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    ) -> dict:
        """Verify authentication and rate limit for REST API endpoints."""
        if fastmcp_auth is None:
            result = {"auth_type": "none"}
        else:
            if not credentials:
                raise HTTPException(
                    status_code=401,
                    detail="Missing authentication credentials",
                    headers={"WWW-Authenticate": 'Bearer realm="mcp"'},
                )

            try:
                access_token = await fastmcp_auth.verify_token(credentials.credentials)
            except Exception as error:
                logger.warning("Bearer token validation failed (%s)", type(error).__name__)
                access_token = None
            if access_token is None:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid or expired credentials",
                    headers={"WWW-Authenticate": 'Bearer realm="mcp"'},
                )
            result = {"auth_type": "bearer", "client_id": access_token.client_id}

        client_id = result.get("client_id", "anonymous")
        if not rest_rate_limiter.allow(client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        return result

    @app.get("/")
    async def root():
        """Root endpoint - redirects to API documentation."""
        from fastapi.responses import RedirectResponse

        return RedirectResponse(url="/docs")

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "ssh-mcp-bridge",
            "version": "2.1.0",
            "auth_enabled": fastmcp_auth is not None,
        }

    # REST API endpoints (for direct HTTP access, not primary MCP interface)
    @app.get("/api/v1/hosts", dependencies=[Depends(verify_authentication)])
    async def list_hosts():
        """List all configured SSH hosts."""
        try:
            return service.list_hosts()
        except Exception as error:
            raise _internal_server_error("Listing hosts", error) from None

    @app.post("/api/v1/execute", dependencies=[Depends(verify_authentication)])
    async def execute_command(request: ExecuteCommandRequest):
        """Execute command on a specific host."""
        try:
            return service.execute_command(request.host, request.command)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as error:
            raise _internal_server_error("Command execution", error) from None

    @app.post("/api/v1/working-directory", dependencies=[Depends(verify_authentication)])
    async def get_working_directory(request: GetWorkingDirectoryRequest):
        """Get current working directory for a host."""
        try:
            return service.get_working_directory(request.host)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as error:
            raise _internal_server_error("Getting working directory", error) from None

    @app.get("/api/v1/file-transfer-config", dependencies=[Depends(verify_authentication)])
    async def get_file_transfer_config():
        """Get file-transfer limits and path policy."""
        try:
            return service.get_file_transfer_config()
        except Exception as error:
            raise _internal_server_error("Getting file-transfer config", error) from None

    @app.post("/api/v1/remote/stat", dependencies=[Depends(verify_authentication)])
    async def stat_remote_path(request: RemotePathRequest):
        """Get metadata for a remote path."""
        try:
            return service.stat_remote_path(request.host, request.remote_path)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as error:
            raise _internal_server_error("Reading remote path metadata", error) from None

    @app.post("/api/v1/remote/list", dependencies=[Depends(verify_authentication)])
    async def list_remote_directory(request: ListRemoteDirectoryRequest):
        """List a remote directory."""
        try:
            return service.list_remote_directory(request.host, request.remote_path, request.limit)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as error:
            raise _internal_server_error("Listing remote directory", error) from None

    @app.post("/api/v1/download", dependencies=[Depends(verify_authentication)])
    async def download_file(request: DownloadFileRequest):
        """Download a remote file to the MCP server filesystem."""
        try:
            return service.download_file(
                request.host,
                request.remote_path,
                request.local_path,
                request.overwrite,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as error:
            raise _internal_server_error("Downloading file", error) from None

    @app.post("/api/v1/upload", dependencies=[Depends(verify_authentication)])
    async def upload_file(request: UploadFileRequest):
        """Upload a file from the MCP server filesystem to a remote host."""
        try:
            return service.upload_file(
                request.host,
                request.local_path,
                request.remote_path,
                request.overwrite,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as error:
            raise _internal_server_error("Uploading file", error) from None

    @app.post("/api/v1/close-session", dependencies=[Depends(verify_authentication)])
    async def close_session(request: CloseSessionRequest):
        """Close SSH session for a host."""
        try:
            return service.close_session(request.host)
        except Exception as error:
            raise _internal_server_error("Closing session", error) from None

    @app.get("/api/v1/stats", dependencies=[Depends(verify_authentication)])
    async def get_stats():
        """Get session statistics."""
        try:
            return service.get_session_stats()
        except Exception as error:
            raise _internal_server_error("Getting session statistics", error) from None

    # Mount FastMCP's HTTP app at root which includes:
    # - Streamable HTTP endpoint at /mcp
    # - OAuth endpoints (/register, /authorize, /token, /auth/callback)
    # - Discovery endpoints (/.well-known/oauth-authorization-server, etc.)
    # - All authentication handling
    #
    # Note: We mount at "" (empty string) so OAuth discovery is at root level
    # where MCP clients expect it (/.well-known/oauth-authorization-server)
    # Mount at root so /mcp and any framework-provided auth discovery routes
    # retain their standard paths.
    app.mount("", mcp_http_app)

    if fastmcp_auth:
        logger.info("FastMCP Streamable HTTP endpoint mounted at /mcp with bearer auth")
    else:
        logger.warning("FastMCP Streamable HTTP endpoint mounted at /mcp without authentication")

    logger.info("HTTP API server created")
    return app
