# Multi-stage build for SSH MCP Bridge
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash mcpuser

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /root/.local /home/mcpuser/.local

# Create writable directories for runtime data (Auth0Provider needs this for storage)
# Also create .ssh directory with proper permissions for mounted keys
RUN mkdir -p /home/mcpuser/.local/share /home/mcpuser/.ssh && \
    chown -R mcpuser:mcpuser /home/mcpuser/.local && \
    chown -R mcpuser:mcpuser /home/mcpuser/.ssh && \
    chmod 700 /home/mcpuser/.ssh

# Copy application code
COPY --chown=mcpuser:mcpuser src/ /app/src/
COPY --chown=mcpuser:mcpuser examples/ /app/examples/
COPY --chown=mcpuser:mcpuser README.md LICENSE /app/

# Set Python path
ENV PYTHONPATH=/app/src
ENV PATH=/home/mcpuser/.local/bin:$PATH

# Switch to non-root user
USER mcpuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command
ENTRYPOINT ["python", "-m", "ssh_mcp_bridge"]
CMD ["config.yaml"]
