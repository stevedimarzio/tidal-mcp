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
- The goal is to build a standalone mcp server for integrating Tidal services with compatibles LLMs, using http/sse protocol
- Include Tidal authentication with oauth2 credentials flow

# Code guidelines
- Include unit tests and integration tests, with very clear, human readable style
- Prevent coupling, rely on inversion of control pattern
- Add ruff for code style
- Use these libs as framework:
  - `pydantic` for data models/dtos and validation
  - `wireup` for injecting services
  - `requests` for external api calls
  - `fastmcp` as base mcp framework
- *Always review and test*

# Build & Deploy specs
- Build output is a docker image with tag vX.Y.Z
- Deploy is intented for cloud container managed services as GCP CloudRun, Azure Container Apps, AWS ECS/Fargate
- Standard ports (8080) and SSE
