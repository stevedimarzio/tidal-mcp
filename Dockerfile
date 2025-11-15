# Multi-stage build for TIDAL MCP server

# Stage 1: Build stage - install dependencies
FROM python:3.11-slim AS builder

# Install uv using pip (simpler and more reliable in Python environment)
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml ./

# Copy application code needed for installation
COPY mcp_server/ ./mcp_server/
COPY tidal_api/ ./tidal_api/

# Install dependencies using uv
RUN uv pip install --system --no-cache .

# Stage 2: Runtime stage
FROM python:3.11-slim

# Install curl for health checks (used by cloud container services)
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Install uv using pip (simpler and more reliable in Python environment)
RUN pip install --no-cache-dir uv

# Create non-root user for security
RUN useradd -m -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy pyproject.toml and application code
COPY pyproject.toml ./
COPY mcp_server/ ./mcp_server/
COPY tidal_api/ ./tidal_api/
COPY start_mcp.py start_mcp_http.py ./

# Install dependencies using uv (as root, then switch to appuser)
RUN uv pip install --system --no-cache .

# Create data directory for sessions and set ownership
RUN mkdir -p /app/data/sessions && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose ports
# 8080: MCP HTTP server (SSE transport)
EXPOSE 8080

# Set environment variables with defaults
# PORT is used by CloudRun and other cloud services
ENV PORT=8080
ENV MCP_HTTP_PORT=8080
ENV HOST=0.0.0.0

# Default command: run MCP server in HTTP mode
CMD ["python", "start_mcp_http.py", "--host", "0.0.0.0"]

