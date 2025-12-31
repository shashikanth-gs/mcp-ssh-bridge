# Docker Deployment Guide

Complete guide for deploying SSH MCP Bridge using Docker.

## Quick Start

```bash
# Pull the official image
docker pull shashikanth-gs/mcp-ssh-bridge:latest

# Run with your configuration
docker run -d \
  --name ssh-mcp-bridge \
  -p 8080:8080 \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v ~/.ssh:/home/mcpuser/.ssh:ro \
  shashikanth-gs/mcp-ssh-bridge:latest
```

## Docker Image

The official Docker image is available at:
- **Docker Hub**: `shashikanth-gs/mcp-ssh-bridge`
- **Architectures**: linux/amd64, linux/arm64

### Image Details

- **Base Image**: python:3.12-slim
- **User**: Non-root user `mcpuser` (UID 1000)
- **Working Directory**: `/app`
- **Exposed Port**: 8080
- **Health Check**: Built-in health endpoint monitoring

## Building from Source

```bash
# Clone repository
git clone https://github.com/shashikanth-gs/mcp-ssh-bridge.git
cd ssh-mcp-bridge

# Build image
docker build -t ssh-mcp-bridge:latest .

# Build for specific platform
docker build --platform linux/amd64 -t ssh-mcp-bridge:amd64 .
docker build --platform linux/arm64 -t ssh-mcp-bridge:arm64 .
```

### Multi-Architecture Build

```bash
# Create buildx builder
docker buildx create --name multiarch --use

# Build for multiple platforms
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t shashikanth-gs/mcp-ssh-bridge:latest \
  --push \
  .
```

## Running the Container

### Basic Run

```bash
docker run -d \
  --name ssh-mcp-bridge \
  -p 8080:8080 \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v ~/.ssh:/home/mcpuser/.ssh:ro \
  shashikanth-gs/mcp-ssh-bridge:latest
```

### With Environment Variables

```bash
docker run -d \
  --name ssh-mcp-bridge \
  -p 8080:8080 \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v ~/.ssh:/home/mcpuser/.ssh:ro \
  -e LOG_LEVEL=DEBUG \
  -e AUTH_MODE=oidc \
  -e IDP_ISSUER=https://auth.example.com/ \
  -e IDP_AUDIENCE=https://ssh-mcp.example.com \
  shashikanth-gs/mcp-ssh-bridge:latest
```

### With Custom Network

```bash
# Create network
docker network create mcp-network

# Run container
docker run -d \
  --name ssh-mcp-bridge \
  --network mcp-network \
  -p 8080:8080 \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v ~/.ssh:/home/mcpuser/.ssh:ro \
  shashikanth-gs/mcp-ssh-bridge:latest
```

### With Resource Limits

```bash
docker run -d \
  --name ssh-mcp-bridge \
  -p 8080:8080 \
  --memory=512m \
  --cpus=1.0 \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v ~/.ssh:/home/mcpuser/.ssh:ro \
  shashikanth-gs/mcp-ssh-bridge:latest
```

## Docker Compose

### Basic Setup

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  ssh-mcp-bridge:
    image: shashikanth-gs/mcp-ssh-bridge:latest
    container_name: ssh-mcp-bridge
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./config.yaml:/app/config.yaml:ro
      - ~/.ssh:/home/mcpuser/.ssh:ro
    environment:
      - LOG_LEVEL=INFO
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

Run with:

```bash
docker-compose up -d
docker-compose logs -f
docker-compose down
```

### With OAuth Configuration

```yaml
version: '3.8'

services:
  ssh-mcp-bridge:
    image: shashikanth-gs/mcp-ssh-bridge:latest
    container_name: ssh-mcp-bridge
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./config.yaml:/app/config.yaml:ro
      - ~/.ssh:/home/mcpuser/.ssh:ro
    environment:
      - LOG_LEVEL=INFO
      - AUTH_MODE=oidc
      - IDP_ISSUER=https://auth.example.com/
      - IDP_AUDIENCE=https://ssh-mcp.example.com
      - IDP_JWKS_URI=https://auth.example.com/.well-known/jwks.json
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### With Reverse Proxy (Nginx)

```yaml
version: '3.8'

services:
  ssh-mcp-bridge:
    image: shashikanth-gs/mcp-ssh-bridge:latest
    container_name: ssh-mcp-bridge
    restart: unless-stopped
    expose:
      - "8080"
    volumes:
      - ./config.yaml:/app/config.yaml:ro
      - ~/.ssh:/home/mcpuser/.ssh:ro
    networks:
      - mcp-network

  nginx:
    image: nginx:alpine
    container_name: nginx-proxy
    restart: unless-stopped
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    networks:
      - mcp-network
    depends_on:
      - ssh-mcp-bridge

networks:
  mcp-network:
    driver: bridge
```

Nginx configuration (`nginx.conf`):

```nginx
events {
    worker_connections 1024;
}

http {
    upstream ssh-mcp-bridge {
        server ssh-mcp-bridge:8080;
    }

    server {
        listen 443 ssl http2;
        server_name ssh-mcp.example.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        location / {
            proxy_pass http://ssh-mcp-bridge;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }

    server {
        listen 80;
        server_name ssh-mcp.example.com;
        return 301 https://$server_name$request_uri;
    }
}
```

## Volume Mounts

### Configuration File

```bash
-v $(pwd)/config.yaml:/app/config.yaml:ro
```

Mount your configuration file as read-only.

### SSH Keys

```bash
-v ~/.ssh:/home/mcpuser/.ssh:ro
```

Mount SSH keys directory as read-only. Ensure permissions are correct:

```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_rsa
```

### Logs (Optional)

```bash
-v $(pwd)/logs:/app/logs
```

Persist logs outside the container.

## Container Management

### View Logs

```bash
# Follow logs
docker logs -f ssh-mcp-bridge

# Last 100 lines
docker logs --tail 100 ssh-mcp-bridge

# With timestamps
docker logs -t ssh-mcp-bridge
```

### Execute Commands in Container

```bash
# Interactive shell
docker exec -it ssh-mcp-bridge /bin/bash

# Run specific command
docker exec ssh-mcp-bridge python -m ssh_mcp_bridge --version
```

### Health Check

```bash
# Manual health check
docker exec ssh-mcp-bridge curl -f http://localhost:8080/health

# Or from host
curl http://localhost:8080/health
```

### Restart Container

```bash
docker restart ssh-mcp-bridge
```

### Stop and Remove

```bash
docker stop ssh-mcp-bridge
docker rm ssh-mcp-bridge
```

## Security Considerations

### Non-Root User

The container runs as non-root user `mcpuser` (UID 1000):

```dockerfile
USER mcpuser
```

### Read-Only Mounts

Mount configuration and SSH keys as read-only:

```bash
-v $(pwd)/config.yaml:/app/config.yaml:ro
-v ~/.ssh:/home/mcpuser/.ssh:ro
```

### No New Privileges

Prevent privilege escalation:

```bash
docker run --security-opt=no-new-privileges:true ...
```

### Resource Limits

Set memory and CPU limits:

```bash
docker run \
  --memory=512m \
  --cpus=1.0 \
  --pids-limit=100 \
  ...
```

### Network Isolation

Use custom networks for isolation:

```bash
docker network create --driver bridge mcp-network
docker run --network mcp-network ...
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs ssh-mcp-bridge

# Verify configuration
docker run --rm -v $(pwd)/config.yaml:/app/config.yaml:ro \
  shashikanth-gs/mcp-ssh-bridge:latest \
  python -m ssh_mcp_bridge --validate /app/config.yaml
```

### Permission Errors

```bash
# Check file ownership
ls -la config.yaml ~/.ssh/id_rsa

# Fix permissions
chmod 600 config.yaml
chmod 600 ~/.ssh/id_rsa
chmod 700 ~/.ssh
```

### SSH Connection Issues

```bash
# Test SSH from container
docker exec ssh-mcp-bridge ssh -i /home/mcpuser/.ssh/id_rsa user@host

# Check network connectivity
docker exec ssh-mcp-bridge ping host
```

### Health Check Failing

```bash
# Manual health check
docker exec ssh-mcp-bridge curl -v http://localhost:8080/health

# Check service is running
docker exec ssh-mcp-bridge ps aux | grep python
```

## Production Deployment

### Using Docker Swarm

```yaml
version: '3.8'

services:
  ssh-mcp-bridge:
    image: shashikanth-gs/mcp-ssh-bridge:latest
    deploy:
      replicas: 2
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
    ports:
      - "8080:8080"
    volumes:
      - ./config.yaml:/app/config.yaml:ro
      - ssh-keys:/home/mcpuser/.ssh:ro
    environment:
      - LOG_LEVEL=INFO

volumes:
  ssh-keys:
    external: true
```

Deploy:

```bash
docker stack deploy -c docker-compose.yml ssh-mcp
```

### Using Kubernetes

See separate Kubernetes deployment documentation for production-grade deployments.

## Updates and Maintenance

### Updating the Image

```bash
# Pull latest image
docker pull shashikanth-gs/mcp-ssh-bridge:latest

# Stop and remove old container
docker stop ssh-mcp-bridge
docker rm ssh-mcp-bridge

# Start new container
docker run -d \
  --name ssh-mcp-bridge \
  -p 8080:8080 \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v ~/.ssh:/home/mcpuser/.ssh:ro \
  shashikanth-gs/mcp-ssh-bridge:latest
```

### Backup and Restore

```bash
# Backup configuration
docker cp ssh-mcp-bridge:/app/config.yaml config-backup.yaml

# Backup logs (if persisted)
docker cp ssh-mcp-bridge:/app/logs logs-backup/
```

## Next Steps

- Review [Configuration Reference](CONFIGURATION.md)
- Set up [Security Best Practices](SECURITY.md)
- Configure [OAuth Authentication](CHATGPT_INTEGRATION.md)
- Learn about [Architecture](ARCHITECTURE.md)
