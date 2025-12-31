"""HTTP server implementation with FastMCP and Auth0."""

import logging
import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ssh_mcp_bridge.models.config import ServerConfig
from ssh_mcp_bridge.services.mcp_service import McpService
from ssh_mcp_bridge.api.mcp_server import create_mcp_server

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


class ExecuteCommandRequest(BaseModel):
    """Request model for execute_command."""

    host: str
    command: str


class GetWorkingDirectoryRequest(BaseModel):
    """Request model for get_working_directory."""

    host: str


class CloseSessionRequest(BaseModel):
    """Request model for close_session."""

    host: str


def create_fastmcp_auth(server_config: ServerConfig):
    """Create FastMCP auth provider based on configuration.
    
    Uses Auth0Provider for full OAuth flow including:
    - Dynamic Client Registration (DCR) for MCP clients
    - OAuth authorization and token endpoints
    - JWT token validation
    - OAuth metadata discovery endpoints
    
    Args:
        server_config: Server configuration with OAuth settings
        
    Returns:
        Auth0Provider instance or None if OAuth is disabled
    """
    if not server_config.oauth or not server_config.oauth.enabled:
        logger.info("OAuth disabled - no authentication configured")
        return None
    
    oauth = server_config.oauth
    
    # Validate required OAuth settings
    if not oauth.issuer or not oauth.audience:
        logger.warning("OAuth enabled but issuer or audience not configured")
        return None
    
    # Get client credentials from environment or config
    client_id = os.environ.get("AUTH0_CLIENT_ID") or getattr(oauth, "client_id", None)
    client_secret = os.environ.get("AUTH0_CLIENT_SECRET") or getattr(oauth, "client_secret", None)
    
    if not client_id or not client_secret:
        logger.warning("OAuth enabled but client_id or client_secret not configured")
        logger.info("Set AUTH0_CLIENT_ID and AUTH0_CLIENT_SECRET environment variables")
        return None
    
    try:
        from fastmcp.server.auth.providers.auth0 import Auth0Provider
        
        # Construct OIDC config URL from issuer
        issuer = oauth.issuer.rstrip("/")
        config_url = f"{issuer}/.well-known/openid-configuration"
        
        # Base URL is the public URL where the server is accessible
        # No /sse prefix needed - FastMCP is mounted at root
        base_url = os.environ.get("BASE_URL", "https://ssh-mcp.k8s.http2xx.io")
        
        # Get JWT signing key for token issuance (optional, defaults to derived from client_secret)
        jwt_signing_key = os.environ.get("JWT_SIGNING_KEY")
        
        auth = Auth0Provider(
            config_url=config_url,
            client_id=client_id,
            client_secret=client_secret,
            audience=oauth.audience,
            base_url=base_url,
            # Optional: customize scopes
            required_scopes=["openid", "profile", "email", "offline_access"],
            # Optional: set specific JWT signing key for production
            jwt_signing_key=jwt_signing_key if jwt_signing_key else client_secret,
            # Disable consent screen for automated MCP clients (optional)
            require_authorization_consent=False,
        )
        
        logger.info(f"Auth0Provider configured:")
        logger.info(f"  Config URL: {config_url}")
        logger.info(f"  Audience: {oauth.audience}")
        logger.info(f"  Base URL: {base_url}")
        
        return auth
        
    except ImportError as e:
        logger.error(f"Failed to import Auth0Provider: {e}")
        logger.error("Make sure fastmcp >= 2.13.0 is installed")
        return None
    except Exception as e:
        logger.error(f"Failed to create Auth0Provider: {e}")
        return None


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
    oauth_enabled = server_config.oauth and server_config.oauth.enabled
    
    app = FastAPI(
        title="SSH MCP Bridge API",
        description="HTTP API for SSH MCP Bridge - Execute commands on SSH hosts securely with OAuth authentication",
        version="2.0.1",
        servers=[
            {"url": "https://ssh-mcp.k8s.http2xx.io", "description": "Production server"}
        ],
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Create FastMCP auth provider (Auth0Provider for full OAuth flow)
    fastmcp_auth = create_fastmcp_auth(server_config)
    
    # Create MCP server with authentication
    mcp_server = create_mcp_server(service, "SSH Bridge", auth=fastmcp_auth)
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=server_config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Simple authentication for REST API endpoints (optional)
    # For full MCP authentication, the FastMCP app handles everything
    async def verify_authentication(
        credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    ) -> dict:
        """Verify authentication for REST API endpoints."""
        if not credentials:
            if oauth_enabled or server_config.api_key:
                raise HTTPException(
                    status_code=401,
                    detail="Missing authentication credentials",
                    headers={"WWW-Authenticate": 'Bearer realm="mcp"'},
                )
            return {"auth_type": "none"}

        token = credentials.credentials

        # API Key authentication for REST endpoints
        if server_config.api_key:
            if token == server_config.api_key:
                return {"auth_type": "api_key"}
        
        # For OAuth tokens, validate using the auth provider
        if oauth_enabled and fastmcp_auth:
            try:
                # Use the auth provider to validate the token
                # This will verify signature, expiry, audience, etc.
                if hasattr(fastmcp_auth, 'validate_token'):
                    # Auth0Provider has validate_token method
                    validated = await fastmcp_auth.validate_token(token)
                    if validated:
                        return {"auth_type": "oauth", "validated": True}
                elif hasattr(fastmcp_auth, '_verify_token'):
                    # Try internal method
                    validated = await fastmcp_auth._verify_token(token)
                    if validated:
                        return {"auth_type": "oauth", "validated": True}
                else:
                    # Fallback: reject if we can't validate
                    raise HTTPException(status_code=401, detail="Token validation not available")
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f"OAuth token validation failed: {e}")
                raise HTTPException(status_code=401, detail="Invalid or expired token")

        raise HTTPException(status_code=401, detail="Invalid credentials")

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
            "version": "2.0.1",
            "auth_enabled": fastmcp_auth is not None,
        }

    # REST API endpoints (for direct HTTP access, not primary MCP interface)
    @app.get("/api/v1/hosts", dependencies=[Depends(verify_authentication)])
    async def list_hosts():
        """List all configured SSH hosts."""
        try:
            return service.list_hosts()
        except Exception as e:
            logger.error(f"Error listing hosts: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/v1/execute", dependencies=[Depends(verify_authentication)])
    async def execute_command(request: ExecuteCommandRequest):
        """Execute command on a specific host."""
        try:
            return service.execute_command(request.host, request.command)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/v1/working-directory", dependencies=[Depends(verify_authentication)])
    async def get_working_directory(request: GetWorkingDirectoryRequest):
        """Get current working directory for a host."""
        try:
            return service.get_working_directory(request.host)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error getting working directory: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/v1/close-session", dependencies=[Depends(verify_authentication)])
    async def close_session(request: CloseSessionRequest):
        """Close SSH session for a host."""
        try:
            return service.close_session(request.host)
        except Exception as e:
            logger.error(f"Error closing session: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/v1/stats", dependencies=[Depends(verify_authentication)])
    async def get_stats():
        """Get session statistics."""
        try:
            return service.get_session_stats()
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # Mount FastMCP's HTTP app at root which includes:
    # - SSE endpoint at /mcp
    # - OAuth endpoints (/register, /authorize, /token, /auth/callback)
    # - Discovery endpoints (/.well-known/oauth-authorization-server, etc.)
    # - All authentication handling
    #
    # Note: We mount at "" (empty string) so OAuth discovery is at root level
    # where MCP clients expect it (/.well-known/oauth-authorization-server)
    try:
        # Get FastMCP's SSE app - it handles auth internally
        mcp_sse_app = mcp_server.http_app(path="/mcp", transport="sse")
        
        # Mount at root so MCP endpoint is at /mcp and OAuth at root level
        app.mount("", mcp_sse_app)
        
        if fastmcp_auth:
            logger.info("FastMCP SSE endpoint mounted at /mcp with Auth0 OAuth")
            logger.info("OAuth endpoints available at /register, /authorize, /token")
            logger.info("OAuth discovery at /.well-known/oauth-authorization-server")
        else:
            logger.info("FastMCP SSE endpoint mounted at /mcp (no authentication)")
    except Exception as e:
        logger.error(f"Could not mount FastMCP SSE endpoint: {e}")
        raise

    logger.info("HTTP API server created")
    return app
