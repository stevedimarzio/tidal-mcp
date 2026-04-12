---
trigger: always_on
---

# General guidelines
- You are an expert developer and architect with solid background on AI,LLM,MCP and software engineering
- Code must stay clean, solid, well architectured and very readable
- Put comments on code only if needed, e.g. in specific complex routines
- Put all generated audits and reports on .local/ folder
- Be solid, always use standard solutions, best practices and state of the art architecture
- If asked to make an analyse or audit on codebase, just answer and NEVER make changes without asking for confirmation
- *ALWAYS FOLLOW THESE GUIDELINES*
- *NEVER MODIFY THIS FILE*

# Project specs
- The goal is to build a standalone MCP server for integrating TIDAL services with compatible LLMs
- Server uses HTTP/SSE transport (ASGI application via FastMCP 2.0)
- Server runs in HTTP mode only (no stdio support)
- Include TIDAL authentication with OAuth2 credentials flow
- Authentication uses X-API-KEY header validation (via API_KEY environment variable)

# Code guidelines
- Include unit tests and integration tests, with very clear, human readable style
- Prevent coupling, rely on inversion of control pattern (IoC container pattern)
- Use ruff for code style and formatting
- Use these libs as framework:
  - `fastmcp>=2.0.0,<3.0.0` as base MCP framework (FastMCP 2.0)
  - `pydantic>=2.0.0` for data models/DTOs and validation
  - `requests>=2.32.3` for external API calls
  - `tidalapi>=0.8.8` for TIDAL API integration
  - `uvicorn>=0.32.0` for ASGI server
- Health check endpoint via `@mcp.custom_route("/health")`
- Middleware configured via `mcp.http_app(middleware=...)` pattern
- FastMCP detailed documentation is in folder docs/fastmcp. You MUST Follow it for code and review.
- *Always review and test*

# Build & Deploy specs
- Build output is a Docker image with tag vX.Y.Z
- Deploy intended for cloud container managed services (AWS ECS/Fargate, Azure Container Apps, FastMCP Cloud)
- Standard port: 8080
- HTTP/SSE transport via ASGI (uvicorn)
- API key authentication via X-API-KEY header (API_KEY env var)
- Health check endpoint at `/health` (bypasses authentication)
