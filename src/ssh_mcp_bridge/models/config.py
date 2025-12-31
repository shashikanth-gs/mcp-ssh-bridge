"""Configuration models."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml


@dataclass
class OAuthConfig:
    """OAuth/OIDC configuration."""

    enabled: bool = False
    issuer: Optional[str] = None
    audience: Optional[str] = None
    jwks_uri: Optional[str] = None

    def __post_init__(self):
        """Load from environment variables if not set."""
        if self.enabled:
            self.issuer = self.issuer or os.getenv("IDP_ISSUER")
            self.audience = self.audience or os.getenv("IDP_AUDIENCE")
            self.jwks_uri = self.jwks_uri or os.getenv("IDP_JWKS_URI")


@dataclass
class ServerConfig:
    """Server configuration."""

    host: str = "0.0.0.0"
    port: int = 8080
    enable_http: bool = False
    enable_stdio: bool = True
    api_key: Optional[str] = None
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    log_level: str = "INFO"
    oauth: Optional[OAuthConfig] = None

    def __post_init__(self):
        """Handle backward compatibility and environment variables."""
        # Load API key from environment if not set
        if not self.api_key:
            self.api_key = os.getenv("API_KEY")
        
        # Initialize OAuth config if not set
        if self.oauth is None:
            # Check if AUTH_MODE is set to oidc in environment
            auth_mode = os.getenv("AUTH_MODE", "api_key").lower()
            if auth_mode == "oidc":
                self.oauth = OAuthConfig(enabled=True)
            else:
                self.oauth = OAuthConfig(enabled=False)


@dataclass
class HostConfig:
    """SSH host configuration."""

    name: str
    description: str = ""
    host: str = ""
    port: int = 22
    username: str = ""
    password: Optional[str] = None
    private_key_path: Optional[str] = None
    execution_mode: str = "exec"  # "exec" or "shell"
    disable_pager: bool = True

    def __post_init__(self):
        """Expand private key path if provided."""
        if self.private_key_path:
            self.private_key_path = os.path.expanduser(self.private_key_path)


@dataclass
class SessionConfig:
    """Session management configuration."""

    idle_timeout: int = 30  # minutes
    max_sessions_per_host: int = 5
    cleanup_interval: int = 60  # seconds


@dataclass
class Config:
    """Main configuration."""

    server: ServerConfig = field(default_factory=ServerConfig)
    hosts: List[HostConfig] = field(default_factory=list)
    session: SessionConfig = field(default_factory=SessionConfig)

    def get_host(self, name: str) -> Optional[HostConfig]:
        """Get host configuration by name."""
        for host in self.hosts:
            if host.name == name:
                return host
        return None


def load_config(config_path: Path) -> Config:
    """Load configuration from YAML file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r") as f:
        data = yaml.safe_load(f)

    # Parse server config with backward compatibility
    server_data = data.get("server", {})
    
    # Handle old 'http_port' key
    if "http_port" in server_data:
        server_data["port"] = server_data.pop("http_port")
    
    # Handle old 'stdio_enabled' key
    if "stdio_enabled" in server_data:
        server_data["enable_stdio"] = server_data.pop("stdio_enabled")
    
    # Default to HTTP mode if stdio_enabled was false
    if not server_data.get("enable_stdio", True):
        server_data["enable_http"] = True
    
    # Parse OAuth config if present
    oauth_data = server_data.pop("oauth", None)
    oauth_config = None
    if oauth_data:
        oauth_config = OAuthConfig(**oauth_data)
    
    # Remove auth section (not part of ServerConfig) - kept for backward compatibility
    server_data.pop("auth", None)
    
    server = ServerConfig(**server_data, oauth=oauth_config)

    # Parse hosts
    hosts = []
    for host_data in data.get("hosts", []):
        hosts.append(HostConfig(**host_data))

    # Parse session config with backward compatibility
    session_data = data.get("session", {})
    
    # Remove unknown keys
    session_data.pop("persist_sessions", None)
    
    session = SessionConfig(**session_data)
    
    # Parse logging config (not used but might be in config)
    # Just ignore it for now
    
    return Config(server=server, hosts=hosts, session=session)
