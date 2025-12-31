# ChatGPT Integration Guide

Complete guide for integrating SSH MCP Bridge with ChatGPT using OAuth 2.0 authentication.

## Overview

ChatGPT can connect to SSH MCP Bridge via HTTP/SSE transport using OAuth 2.0 for authentication. This enables ChatGPT to securely manage your infrastructure without exposing credentials.

## Prerequisites

- SSH MCP Bridge deployed with HTTP mode enabled
- OAuth 2.0 / OIDC provider (Auth0, Azure AD, Okta, Keycloak, etc.)
- Domain name with HTTPS (required for ChatGPT)
- ChatGPT Plus or Enterprise subscription

## Architecture

```
ChatGPT
   |
   | 1. Discovers OAuth metadata
   v
/.well-known/oauth-protected-resource
   |
   | 2. Redirects user to OAuth provider
   v
OAuth Provider (Auth0/Azure AD/etc.)
   |
   | 3. User authenticates
   | 4. Returns authorization code
   v
ChatGPT exchanges code for JWT token
   |
   | 5. Calls MCP API with Bearer token
   v
SSH MCP Bridge
   |
   | 6. Validates JWT
   | 7. Executes SSH commands
   v
SSH Servers
```

## Step 1: Deploy SSH MCP Bridge

### Configuration

Create `config.yaml`:

```yaml
server:
  host: "0.0.0.0"
  port: 8080
  enable_http: true
  enable_stdio: false
  
  oauth:
    enabled: true
    issuer: "https://your-domain.auth0.com/"
    audience: "https://ssh-mcp.yourdomain.com"
    jwks_uri: "https://your-domain.auth0.com/.well-known/jwks.json"
  
  cors_origins:
    - "https://chat.openai.com"
    - "https://chatgpt.com"
  
  log_level: "INFO"

hosts:
  - name: web-server
    description: "Production web server"
    host: "your-server.com"
    username: "admin"
    private_key_path: "~/.ssh/id_rsa"
    execution_mode: "shell"

session:
  idle_timeout: 30
  max_sessions_per_host: 5
```

### Deploy with Docker

```bash
docker run -d \
  --name ssh-mcp-bridge \
  -p 8080:8080 \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v ~/.ssh:/home/mcpuser/.ssh:ro \
  -e AUTH_MODE=oidc \
  -e IDP_ISSUER=https://your-domain.auth0.com/ \
  -e IDP_AUDIENCE=https://ssh-mcp.yourdomain.com \
  shashikanth-gs/mcp-ssh-bridge:latest
```

### Set Up HTTPS

ChatGPT requires HTTPS. Use a reverse proxy (Nginx, Caddy, Traefik):

```nginx
server {
    listen 443 ssl http2;
    server_name ssh-mcp.yourdomain.com;

    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;

    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Step 2: Configure OAuth Provider

### Option A: Auth0

1. **Create an API**:
   - Go to Applications > APIs > Create API
   - Name: "SSH MCP Bridge API"
   - Identifier: `https://ssh-mcp.yourdomain.com`
   - Signing Algorithm: RS256

2. **Configure Scopes**:
   - Add scope: `mcp:execute` - "Execute MCP operations"
   - Add scope: `openid` - "OpenID Connect"
   - Add scope: `profile` - "User profile"
   - Add scope: `email` - "User email"

3. **Create an Application**:
   - Go to Applications > Create Application
   - Name: "ChatGPT MCP Connector"
   - Type: Regular Web Application
   - Allowed Callback URLs: 
     - `https://chatgpt.com/aip/callback`
     - `https://chat.openai.com/aip/callback`

4. **Configure Token Settings**:
   - Token Endpoint Authentication Method: `client_secret_basic`
   - Grant Types: Authorization Code, Refresh Token

5. **Create Auth0 Action** (to force scopes):
   - Go to Actions > Flows > Login
   - Create Custom Action:

```javascript
exports.onExecutePostLogin = async (event, api) => {
  const namespace = 'https://ssh-mcp.yourdomain.com';
  
  // Add user claims
  api.accessToken.setCustomClaim(`${namespace}/email`, event.user.email);
  api.accessToken.setCustomClaim(`${namespace}/user_id`, event.user.user_id);
  api.accessToken.setCustomClaim(`${namespace}/name`, event.user.name || event.user.email);
  
  // Force required scopes
  const requiredScopes = ["openid", "profile", "email", "mcp:execute"];
  requiredScopes.forEach(scope => {
    api.accessToken.addScope(scope);
  });
};
```

6. **Get Credentials**:
   - Client ID: Found in Application settings
   - Client Secret: Found in Application settings (keep secure)

### Option B: Azure AD

1. **Register Application**:
   - Go to Azure Portal > Azure Active Directory > App registrations
   - New registration
   - Name: "SSH MCP Bridge"
   - Redirect URI: `https://chatgpt.com/aip/callback`

2. **Expose an API**:
   - Go to Expose an API
   - Set Application ID URI: `api://ssh-mcp-bridge`
   - Add scope: `mcp.execute`

3. **Add API Permissions**:
   - Microsoft Graph: `openid`, `profile`, `email`
   - Your API: `mcp.execute`

4. **Create Client Secret**:
   - Go to Certificates & secrets
   - New client secret
   - Save the secret value

5. **Configure Token**:
   - Token version: 2.0
   - Issuer: `https://login.microsoftonline.com/{tenant-id}/v2.0`

### Option C: Okta

1. **Create Authorization Server**:
   - Security > API > Authorization Servers
   - Add Authorization Server
   - Name: "SSH MCP Bridge"
   - Audience: `https://ssh-mcp.yourdomain.com`

2. **Add Scopes**:
   - `openid`, `profile`, `email`, `mcp:execute`

3. **Create Application**:
   - Applications > Create App Integration
   - Sign-in method: OIDC
   - Application type: Web Application
   - Sign-in redirect URIs: `https://chatgpt.com/aip/callback`

4. **Get Credentials**:
   - Client ID and Secret from application settings

### Option D: Keycloak

1. **Create Realm**:
   - Create new realm: "mcp"

2. **Create Client**:
   - Clients > Create
   - Client ID: "ssh-mcp-bridge"
   - Client Protocol: openid-connect
   - Access Type: confidential
   - Valid Redirect URIs: `https://chatgpt.com/aip/callback`

3. **Configure Client Scopes**:
   - Add custom scopes: `mcp:execute`

4. **Get Credentials**:
   - Credentials tab > Client Secret

## Step 3: Configure ChatGPT

1. **Enable Developer Mode**:
   - Go to ChatGPT Settings
   - Enable "Developer mode" or "Beta features"

2. **Add MCP Server**:
   - Go to Settings > Apps > MCP Servers
   - Click "Add Server" or "Connect"

3. **Enter Configuration**:

   **Server URL**:
   ```
   https://ssh-mcp.yourdomain.com
   ```

   **Authentication Type**: OAuth 2.0

   **OAuth Configuration**:
   - **Authorization URL**: `https://your-domain.auth0.com/authorize` (or your provider)
   - **Token URL**: `https://your-domain.auth0.com/oauth/token` (or your provider)
   - **Client ID**: Your OAuth application client ID
   - **Client Secret**: Your OAuth application client secret
   - **Scope**: `openid profile email mcp:execute`

4. **Test Connection**:
   - ChatGPT will redirect you to your OAuth provider
   - Log in and authorize the application
   - ChatGPT will receive the JWT token
   - Connection should be established

## Step 4: Using ChatGPT with SSH MCP Bridge

Once connected, you can ask ChatGPT to manage your servers:

### Example Prompts

**List servers**:
```
Show me all available SSH servers
```

**Check system status**:
```
Check the uptime and disk usage on web-server
```

**Deploy application**:
```
On web-server:
1. Pull the latest code from git
2. Install dependencies
3. Restart the application service
```

**Multi-server orchestration**:
```
I need to deploy a new feature:
1. Create database migration on db-server
2. Deploy backend code on app-server
3. Update nginx config on web-server
4. Test the deployment
```

**Troubleshooting**:
```
The website is slow. Can you:
1. Check CPU and memory usage on all servers
2. Review nginx access logs for errors
3. Check database query performance
4. Suggest optimizations
```

## Security Considerations

### Token Security

- JWT tokens are validated on every request
- Tokens include user identity (email, name, ID)
- Tokens expire after the configured lifetime (typically 24 hours)
- Refresh tokens enable seamless re-authentication

### Audit Logging

All commands are logged with:
- Timestamp
- User identity (from JWT claims)
- Target host
- Executed command
- Command result

Example log entry:
```
2025-12-31 10:23:45 INFO User: user@example.com executed on web-server: uptime
```

### Access Control

- Configure which servers are accessible via the `hosts` section
- Use OAuth scopes to control access levels
- Implement OAuth provider-level access policies

### Network Security

- HTTPS is mandatory for ChatGPT integration
- Use strong SSL/TLS certificates
- Configure firewall rules to restrict access
- Consider using VPN or private network for SSH servers

## Troubleshooting

### OAuth Discovery Fails

**Problem**: ChatGPT cannot discover OAuth metadata

**Solution**:
```bash
# Verify discovery endpoint
curl https://ssh-mcp.yourdomain.com/.well-known/oauth-protected-resource

# Should return:
{
  "resource": "https://ssh-mcp.yourdomain.com",
  "authorization_servers": ["https://your-domain.auth0.com/"],
  "scopes_supported": ["openid", "profile", "email", "mcp:execute"],
  "bearer_methods_supported": ["header"]
}
```

### "Not all requested permissions were granted"

**Problem**: OAuth provider not granting all scopes

**Solution**:
- Use Auth0 Action to force scopes (see Auth0 setup above)
- Or set Default Audience in Auth0 tenant settings
- Or configure application-level scope requirements

### JWT Validation Fails

**Problem**: Token rejected with 401 Unauthorized

**Solution**:
```bash
# Check JWT claims
# Decode token at jwt.io or:
echo "YOUR_TOKEN" | cut -d. -f2 | base64 -d | jq

# Verify issuer and audience match configuration
# Check token expiration
# Ensure JWKS URI is accessible
```

### Connection Timeout

**Problem**: ChatGPT times out connecting to server

**Solution**:
- Verify HTTPS is configured correctly
- Check firewall rules allow inbound HTTPS
- Test server accessibility: `curl https://ssh-mcp.yourdomain.com/health`
- Review server logs for errors

## Advanced Configuration

### Custom Claims

Add custom user information to JWT tokens:

```javascript
// Auth0 Action
api.accessToken.setCustomClaim('https://ssh-mcp.yourdomain.com/department', event.user.user_metadata.department);
api.accessToken.setCustomClaim('https://ssh-mcp.yourdomain.com/role', event.user.app_metadata.role);
```

### Scope-Based Access Control

Implement different access levels:

```yaml
# Future enhancement - example configuration
hosts:
  - name: production-db
    description: "Production database"
    required_scopes:
      - "mcp:execute"
      - "mcp:admin"
```

### Rate Limiting

Implement rate limiting at the OAuth provider or reverse proxy level to prevent abuse.

## Monitoring

### Health Checks

```bash
# Server health
curl https://ssh-mcp.yourdomain.com/health

# Session statistics
curl -H "Authorization: Bearer TOKEN" \
  https://ssh-mcp.yourdomain.com/api/v1/stats
```

### Logs

Monitor application logs for:
- Authentication events
- Command execution
- Errors and warnings
- Performance metrics

```bash
# Docker logs
docker logs -f ssh-mcp-bridge

# Filter for OAuth events
docker logs ssh-mcp-bridge | grep -i oauth
```

## Next Steps

- Review [Security Best Practices](SECURITY.md)
- Configure [Additional MCP Clients](QUICKSTART.md)
- Set up [Monitoring and Alerting](DOCKER.md)
- Explore [Advanced Configuration](CONFIGURATION.md)
