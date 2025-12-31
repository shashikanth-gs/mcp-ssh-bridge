# Security Best Practices

Comprehensive security guide for SSH MCP Bridge deployment.

## Security Model

SSH MCP Bridge implements a defense-in-depth security model:

1. **Credential Isolation**: AI agents never see actual IPs, passwords, or SSH keys
2. **Authentication**: API key or OAuth 2.0/OIDC for HTTP access
3. **Authorization**: Configuration-based access control
4. **Audit Logging**: Complete command history with user context
5. **Session Management**: Automatic timeout and cleanup
6. **Container Security**: Non-root execution, resource limits

## Credential Management

### SSH Key Security

**Generate secure SSH keys**:
```bash
# Generate ED25519 key (recommended)
ssh-keygen -t ed25519 -f ~/.ssh/mcp_bridge_key

# Or RSA 4096-bit
ssh-keygen -t rsa -b 4096 -f ~/.ssh/mcp_bridge_rsa_key
```

**Set correct permissions**:
```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/mcp_bridge_key
chmod 644 ~/.ssh/mcp_bridge_key.pub
```

**Use dedicated keys per server**:
```yaml
hosts:
  - name: web-server
    private_key_path: "~/.ssh/web_server_key"
  
  - name: db-server
    private_key_path: "~/.ssh/db_server_key"
```

**Never use password authentication** in production:
```yaml
# Bad - avoid this
hosts:
  - name: server
    password: "plaintext-password"

# Good - use SSH keys
hosts:
  - name: server
    private_key_path: "~/.ssh/id_rsa"
```

### Configuration File Security

**Restrict file permissions**:
```bash
chmod 600 config.yaml
chown $USER:$USER config.yaml
```

**Use environment variables for secrets**:
```bash
# Instead of storing in config.yaml
export SSH_MCP_API_KEY=$(openssl rand -hex 32)
export IDP_ISSUER=https://auth.example.com/
export IDP_AUDIENCE=https://ssh-mcp.example.com
```

**Never commit secrets to Git**:
```bash
# Add to .gitignore
echo "config.yaml" >> .gitignore
echo "*.key" >> .gitignore
echo ".env" >> .gitignore
```

**Use secrets management tools**:
- HashiCorp Vault
- AWS Secrets Manager
- Azure Key Vault
- Kubernetes Secrets

## Authentication

### API Key Authentication

**Generate strong API keys**:
```bash
# Generate 256-bit key
openssl rand -hex 32

# Or use Python
python -c "import secrets; print(secrets.token_hex(32))"
```

**Configure in server**:
```yaml
server:
  enable_http: true
  api_key: "REPLACE_WITH_GENERATED_KEY"
```

**Rotate keys regularly**:
- Change API keys every 90 days
- Use different keys for different environments
- Revoke old keys immediately after rotation

### OAuth 2.0 / OIDC (Recommended for Production)

**Use OAuth for HTTP deployments**:
```yaml
server:
  oauth:
    enabled: true
    issuer: "https://auth.example.com/"
    audience: "https://ssh-mcp.example.com"
```

**Benefits**:
- Centralized authentication
- User identity tracking
- Token expiration and refresh
- Revocation support
- SSO integration

**Token validation**:
- JWT signature verification (RS256)
- Issuer validation
- Audience validation
- Expiration checking
- Custom claims extraction

## Authorization

### Host-Level Access Control

**Principle of least privilege**:
```yaml
# Create separate SSH users with minimal permissions
hosts:
  - name: web-server
    username: "web-readonly"  # Read-only user
    description: "Web server (read-only access)"
```

**Restrict sudo access**:
```bash
# On SSH server, configure sudoers
web-readonly ALL=(ALL) NOPASSWD: /usr/bin/systemctl status nginx
web-readonly ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx
```

**Use execution_mode wisely**:
```yaml
# exec mode (safer) for sensitive operations
hosts:
  - name: production-db
    execution_mode: "exec"  # Stateless, isolated

# shell mode for trusted operations
hosts:
  - name: dev-server
    execution_mode: "shell"  # Stateful, persistent
```

### Network-Level Access Control

**Firewall rules**:
```bash
# Allow only from specific IPs
ufw allow from 192.168.1.0/24 to any port 8080

# Or use iptables
iptables -A INPUT -p tcp -s 192.168.1.0/24 --dport 8080 -j ACCEPT
iptables -A INPUT -p tcp --dport 8080 -j DROP
```

**Use VPN or private network**:
- Deploy SSH MCP Bridge on internal network
- Access via VPN tunnel
- Use Tailscale, Wireguard, or similar

**SSH server hardening**:
```bash
# /etc/ssh/sshd_config
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AllowUsers web-readonly db-admin
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
```

## Audit Logging

### Enable Detailed Logging

**Configure log level**:
```yaml
server:
  log_level: "INFO"  # INFO for production, DEBUG for troubleshooting
```

**Log command execution**:
All commands are automatically logged with:
- Timestamp
- User identity (from JWT or API key)
- Target host
- Command executed
- Exit status
- Output (configurable)

**Example log entry**:
```
2025-12-31 14:23:45 INFO [user@example.com] web-server: uptime
2025-12-31 14:23:45 INFO [user@example.com] web-server: SUCCESS (exit 0)
```

### Centralized Logging

**Send logs to SIEM**:
```bash
# Forward logs to syslog
docker run \
  --log-driver=syslog \
  --log-opt syslog-address=udp://siem.example.com:514 \
  shashikanth-gs/mcp-ssh-bridge:latest
```

**Use log aggregation**:
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Splunk
- Datadog
- CloudWatch Logs

### Monitoring and Alerting

**Monitor for suspicious activity**:
- Failed authentication attempts
- Commands executed as root
- Access to production systems
- High-privilege operations (rm, chmod, etc.)
- After-hours access

**Set up alerts**:
```bash
# Example: Alert on suspicious commands
grep -i "rm -rf\|sudo su\|passwd" /var/log/ssh-mcp-bridge.log \
  | mail -s "Suspicious SSH MCP Activity" security@example.com
```

## Network Security

### HTTPS/TLS

**Always use HTTPS in production**:
```nginx
# Nginx configuration
server {
    listen 443 ssl http2;
    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;
    
    # Strong SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000" always;
}
```

**Use Let's Encrypt for free certificates**:
```bash
certbot --nginx -d ssh-mcp.example.com
```

### CORS Configuration

**Restrict origins**:
```yaml
server:
  cors_origins:
    - "https://chat.openai.com"
    - "https://chatgpt.com"
    - "https://yourdomain.com"
  # Never use "*" in production
```

### Rate Limiting

**Implement at reverse proxy**:
```nginx
# Nginx rate limiting
limit_req_zone $binary_remote_addr zone=mcp:10m rate=10r/s;

server {
    location / {
        limit_req zone=mcp burst=20 nodelay;
    }
}
```

## Container Security

### Non-Root Execution

**Docker runs as non-root**:
```dockerfile
USER mcpuser
```

**Verify**:
```bash
docker exec ssh-mcp-bridge whoami
# Output: mcpuser
```

### Resource Limits

**Set memory and CPU limits**:
```yaml
# docker-compose.yml
services:
  ssh-mcp-bridge:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

**Set process limits**:
```bash
docker run --pids-limit=100 ...
```

### Read-Only Filesystem

**Mount volumes as read-only**:
```bash
docker run \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v ~/.ssh:/home/mcpuser/.ssh:ro \
  ...
```

**Consider read-only root filesystem**:
```bash
docker run --read-only ...
```

### Security Options

**Enable security features**:
```bash
docker run \
  --security-opt=no-new-privileges:true \
  --cap-drop=ALL \
  --cap-add=NET_BIND_SERVICE \
  ...
```

## Secrets Management

### HashiCorp Vault

```bash
# Store secrets in Vault
vault kv put secret/ssh-mcp/api-key value="YOUR_KEY"
vault kv put secret/ssh-mcp/ssh-keys/web-server value="@~/.ssh/web_server_key"

# Retrieve in application
export SSH_MCP_API_KEY=$(vault kv get -field=value secret/ssh-mcp/api-key)
```

### Kubernetes Secrets

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: ssh-mcp-secrets
type: Opaque
data:
  api-key: BASE64_ENCODED_KEY
  ssh-key: BASE64_ENCODED_SSH_KEY
```

### AWS Secrets Manager

```bash
# Store secret
aws secretsmanager create-secret \
  --name ssh-mcp/api-key \
  --secret-string "YOUR_API_KEY"

# Retrieve in application
export SSH_MCP_API_KEY=$(aws secretsmanager get-secret-value \
  --secret-id ssh-mcp/api-key \
  --query SecretString \
  --output text)
```

## Incident Response

### Preparation

1. **Document access**:
   - Who has access to SSH MCP Bridge
   - Who has access to SSH servers
   - Emergency contacts

2. **Enable logging**:
   - Centralized log collection
   - Log retention policy (90+ days)
   - Backup logs regularly

3. **Create runbooks**:
   - How to revoke access
   - How to rotate keys
   - How to investigate incidents

### Detection

**Monitor for**:
- Unusual command patterns
- Access from unexpected locations
- Failed authentication attempts
- Privilege escalation attempts
- Data exfiltration attempts

### Response

**Immediate actions**:
1. Disable compromised accounts
2. Rotate all API keys and SSH keys
3. Review audit logs
4. Isolate affected systems
5. Notify security team

**Revoke access**:
```bash
# Disable OAuth tokens
# (varies by provider)

# Rotate API key
# Update config.yaml and restart server

# Revoke SSH keys
ssh-keygen -R hostname
# Remove key from ~/.ssh/authorized_keys on servers
```

## Compliance

### GDPR / Data Privacy

- Log only necessary information
- Implement data retention policies
- Provide mechanism for data deletion
- Secure personal data (email, names)

### SOC 2 / ISO 27001

- Implement access controls
- Enable audit logging
- Regular security reviews
- Incident response procedures
- Change management

### Industry-Specific

- **HIPAA**: Encrypt data in transit and at rest
- **PCI DSS**: Restrict access to cardholder data
- **FedRAMP**: Use approved cryptographic modules

## Security Checklist

Before deploying to production:

- [ ] SSH key authentication only (no passwords)
- [ ] Strong API keys or OAuth 2.0
- [ ] HTTPS with valid certificates
- [ ] Restrictive firewall rules
- [ ] File permissions (600 for config and keys)
- [ ] Non-root container execution
- [ ] Resource limits configured
- [ ] Audit logging enabled
- [ ] Centralized log collection
- [ ] Monitoring and alerting configured
- [ ] Secrets not in Git repository
- [ ] Regular key rotation schedule
- [ ] Incident response plan documented
- [ ] Minimal SSH user permissions
- [ ] CORS properly configured
- [ ] Rate limiting enabled
- [ ] Security updates automated

## Regular Maintenance

### Weekly

- Review audit logs for anomalies
- Check for failed authentication attempts
- Verify monitoring and alerting is working

### Monthly

- Review user access list
- Test incident response procedures
- Update dependencies

### Quarterly

- Rotate API keys
- Rotate SSH keys
- Security audit
- Penetration testing
- Review and update firewall rules

### Annually

- Comprehensive security review
- Update security policies
- Security awareness training
- Disaster recovery testing

## Reporting Security Issues

If you discover a security vulnerability:

1. **Do not** open a public GitHub issue
2. Email security contact (add your contact here)
3. Include detailed description
4. Provide steps to reproduce
5. Allow time for patch development

## Additional Resources

- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [SSH Security Best Practices](https://www.ssh.com/academy/ssh/security)
- [OAuth 2.0 Security Best Current Practice](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-security-topics)

## Next Steps

- Review [Configuration Reference](CONFIGURATION.md)
- Set up [OAuth Authentication](CHATGPT_INTEGRATION.md)
- Learn about [Docker Deployment](DOCKER.md)
- Understand [Architecture](ARCHITECTURE.md)
