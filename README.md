# TIDAL MCP: My Custom Picks 🌟🎧

![Demo: Music Recommendations in Action](./assets/tidal_mcp_demo.gif)

Most music platforms offer recommendations — Daily Discovery, Top Artists, New Arrivals, etc. — but even with the state-of-the-art system, they often feel too "aggregated". I wanted something more custom and context-aware.

With TIDAL MCP, you can ask for things like:
> *"Based on my last 10 favorites, find similar tracks — but only ones from recent years."*
>
> *"Find me tracks like those in this playlist, but slower and more acoustic."*

The LLM filters and curates results using your input, finds similar tracks via TIDAL’s API, and builds new playlists directly in your account.

<a href="https://glama.ai/mcp/servers/@yuhuacheng/tidal-mcp">
  <img width="400" height="200" src="https://glama.ai/mcp/servers/@yuhuacheng/tidal-mcp/badge" alt="TIDAL: My Custom Picks MCP server" />
</a>

## Features

- 🔐 **OAuth2 Authentication**: Secure browser-based login flow for TIDAL account access
- 🌟 **Music Recommendations**: Get personalized track recommendations based on your favorites or specific tracks, with custom filtering criteria
- 📋 **Playlist Management**: Create, view, browse, and delete your TIDAL playlists
- 🔍 **Music Search**: Search TIDAL's catalog for tracks, albums, and artists
- ❤️ **Favorites Access**: Retrieve and explore your favorite tracks
- 🐳 **Docker Support**: Run in containers with health checks for cloud deployment

## Quick Start

### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- TIDAL subscription

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yuhuacheng/tidal-mcp.git
   cd tidal-mcp
   ```

2. Install dependencies using uv (no need to create a virtual environment manually):
   ```bash
   uv pip install --editable .
   ```

   This will install all dependencies defined in the pyproject.toml file and set up the project in development mode.

### Running the Server

To run the MCP server directly for testing:

```bash
# Option 1: Using the start script (stdio mode - for Claude Desktop)
uv run python start_mcp.py

# Option 2: Using uv with mcp command directly
uv run mcp run mcp_server/server.py

# Option 3: HTTP mode (for debugging with Cursor)
uv run python start_mcp_http.py --port 8080
```

**Note:** Always use `uv run` to ensure all dependencies are available in the correct environment.

**HTTP Mode for Debugging:** If you want to debug the MCP server or connect it to Cursor via HTTP, use `start_mcp_http.py`. See [HTTP Debug Setup Guide](docs/HTTP_DEBUG_SETUP.md) for detailed instructions.

### Running with Docker

You can also run the TIDAL MCP server using Docker, which simplifies deployment and ensures consistent environments.

#### Prerequisites

- Docker and Docker Compose installed
- TIDAL subscription

#### Building the Docker Image

**For local development:**
```bash
docker build -t tidal-mcp:latest .
```

**For CloudRun/cloud deployment (required for CloudRun):**
CloudRun requires `linux/amd64` architecture. Build with the correct platform:

```bash
docker buildx build --platform linux/amd64 -t tidal-mcp:latest .
```

Or use the task command:
```bash
task docker-build-cloud
```

**⚠️ Important:** If you're building on Apple Silicon (M1/M2/M3 Mac), you must specify `--platform linux/amd64` for CloudRun deployment, otherwise you'll get an "exec format error".

#### Running with Docker

**Option 1: Using Docker Compose (Recommended)**

The easiest way to run the server is using Docker Compose:

```bash
docker compose up
```

Or use the task command:

```bash
task docker-dev
```

This will:
- Build the image if it doesn't exist
- Start the server in HTTP mode on port 8080
- Mount the `data/sessions` directory for session persistence
- Run health checks using curl (as cloud services do)
- Enable API key authentication with default dev key: `mcptest` (via `x-api-key` header)

To run in detached mode:

```bash
docker compose up -d
```

To stop the server:

```bash
docker compose down
```

**Option 2: Using Docker directly**

Run the container with HTTP mode (default):

```bash
docker run -p 8080:8080 \
  -v $(pwd)/data/sessions:/app/data/sessions \
  tidal-mcp:latest
```

Run in stdio mode:

```bash
docker run tidal-mcp:latest python start_mcp.py
```

#### Environment Variables

You can customize the server behavior using environment variables:

- `PORT` or `MCP_HTTP_PORT`: Port for the MCP HTTP server (default: `8080`, CloudRun compatible)
- `HOST`: Host to bind to (default: `0.0.0.0` for Docker, `127.0.0.1` for local)
- `API_KEY` or `MCP_API_KEY`: API key for authentication via `x-api-key` header (default in docker-compose: `mcptest` for development, **change in production!**)

Example with custom port:

```bash
docker run -p 9000:9000 \
  -e PORT=9000 \
  -v $(pwd)/data/sessions:/app/data/sessions \
  tidal-mcp:latest
```

Or with docker-compose, modify the `environment` section in `docker-compose.yml`.

#### Volume Mounts

The `data/sessions` directory is mounted as a volume to persist TIDAL authentication sessions across container restarts. This ensures you don't need to re-authenticate every time the container is restarted.

#### Connecting to the Docker Container

When running in HTTP mode, connect your MCP client to:

```
http://localhost:8080/sse
```

**Note:** The Docker Compose setup uses API key authentication by default (dev key: `mcptest`). You must include the `x-api-key` header in your requests.

For Cursor configuration, use:

```json
{
  "mcpServers": {
    "TIDAL MCP (Docker)": {
      "url": "http://localhost:8080/sse",
      "transport": "sse",
      "headers": {
        "x-api-key": "mcptest"
      }
    }
  }
}
```

**⚠️ Important:** The default API key `mcptest` is for **development only**. For production deployments, set a strong, unique API key via the `API_KEY` environment variable.

### Cloud Deployment (CloudRun, ECS, Azure Container Apps)

The container is designed to work with cloud container services. Here's how to configure it:

#### Google Cloud Run

1. **Build your Docker image for CloudRun** (must be linux/amd64):
   ```bash
   docker buildx build --platform linux/amd64 -t gcr.io/YOUR_PROJECT_ID/tidal-mcp:latest .
   ```

2. **Push to Google Container Registry or Artifact Registry**:
   ```bash
   docker push gcr.io/YOUR_PROJECT_ID/tidal-mcp:latest
   ```

3. **Deploy to CloudRun** with environment variables:

```bash
gcloud run deploy tidal-mcp \
  --image gcr.io/YOUR_PROJECT_ID/tidal-mcp:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars API_KEY=your-production-api-key-here \
  --port 8080
```

Or using the Cloud Console:
- Go to Cloud Run → Create Service
- Set the container image
- Under **Container, Networking, Security** → **Variables & Secrets**:
  - Add environment variable: `API_KEY` = `your-production-api-key-here`
  - The `PORT` variable is automatically set by CloudRun (defaults to 8080)

3. **Access your service**: CloudRun will provide a URL like `https://tidal-mcp-xxxxx.run.app`

4. **Configure your MCP client** to use the CloudRun URL with the API key:

```json
{
  "mcpServers": {
    "TIDAL MCP (CloudRun)": {
      "url": "https://tidal-mcp-xxxxx.run.app/sse",
      "transport": "sse",
      "headers": {
        "x-api-key": "your-production-api-key-here"
      }
    }
  }
}
```

**Security Best Practices:**
- Use Google Secret Manager for sensitive values:
  ```bash
  gcloud run deploy tidal-mcp \
    --image gcr.io/YOUR_PROJECT_ID/tidal-mcp:latest \
    --update-secrets API_KEY=api-key-secret:latest
  ```
- Never commit API keys to version control
- Use different API keys for different environments (dev, staging, prod)
- Rotate API keys regularly

#### AWS ECS / Fargate

Set the `API_KEY` environment variable in your task definition:

```json
{
  "containerDefinitions": [{
    "name": "tidal-mcp",
    "image": "your-ecr-repo/tidal-mcp:latest",
    "environment": [
      {
        "name": "API_KEY",
        "value": "your-production-api-key-here"
      },
      {
        "name": "PORT",
        "value": "8080"
      }
    ],
    "portMappings": [{
      "containerPort": 8080
    }]
  }]
}
```

#### Azure Container Apps

Set environment variables in your Container App configuration:

```bash
az containerapp create \
  --name tidal-mcp \
  --resource-group your-resource-group \
  --image your-registry.azurecr.io/tidal-mcp:latest \
  --target-port 8080 \
  --env-vars API_KEY=your-production-api-key-here PORT=8080
```

**Note:** The `/health` endpoint bypasses API key authentication, which is required for cloud health checks to work properly.

## MCP Client Configuration

### Claude Desktop Configuration

To integrate TIDAL MCP with Claude Desktop, you need to add the server configuration to Claude's MCP settings.

#### Step 1: Find Your Paths

Before configuring, you'll need to know:

1. **Path to `uv` executable**: 
   - macOS (Homebrew): Usually `/opt/homebrew/bin/uv` or `/usr/local/bin/uv`
   - Linux: Usually `~/.local/bin/uv` or `/usr/local/bin/uv`
   - Find it by running: `which uv` in your terminal

2. **Path to your project**: 
   - The full path to where you cloned this repository
   - Example: `/Users/yourname/projects/tidal-mcp`

#### Step 2: Locate Claude Desktop Config File

The configuration file location depends on your operating system:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

#### Step 3: Edit the Configuration

1. Open Claude Desktop
2. Go to **Settings** → **Developer**
3. Click **"Edit Config"** (this opens the config file in your default editor)
4. Add or update the `mcpServers` section with the following configuration:

```json
{
  "mcpServers": {
    "TIDAL Integration": {
      "command": "/opt/homebrew/bin/uv",
      "env": {},
      "args": [
        "run",
        "--with",
        "requests",
        "--with",
        "mcp[cli]",
        "--with",
        "fastapi",
        "--with",
        "uvicorn",
        "--with",
        "tidalapi",
        "mcp",
        "run",
        "/path/to/your/tidal-mcp/mcp_server/server.py"
      ]
    }
  }
}
```

**Important**: Replace the following in the configuration:
- `/opt/homebrew/bin/uv` → Your actual `uv` path (from Step 1)
- `/path/to/your/tidal-mcp/mcp_server/server.py` → Your actual project path (from Step 1)

#### Step 4: Save and Restart

1. Save the configuration file
2. Restart Claude Desktop completely (quit and reopen)
3. The TIDAL Integration should now appear in Claude's MCP tools

#### Alternative Configuration (Using start_mcp.py)

If you prefer to use the start script directly, you can use this alternative configuration:

```json
{
  "mcpServers": {
    "TIDAL Integration": {
      "command": "/opt/homebrew/bin/uv",
      "env": {},
      "args": [
        "run",
        "python",
        "/path/to/your/tidal-mcp/start_mcp.py"
      ]
    }
  }
}
```

#### Verification

After restarting Claude Desktop:

1. Start a new conversation
2. Look for the TIDAL Integration tools in Claude's available tools
3. Try asking: *"Can you help me log in to TIDAL?"*

Example screenshot of the MCP configuration in Claude Desktop:
![Claude MCP Configuration](./assets/claude_desktop_config.png)

### Cursor Configuration (HTTP Mode for Debugging)

To use the MCP server with Cursor in HTTP mode for debugging:

1. **Start the server in HTTP mode:**
   
   **Option A: Local development (no API key required):**
   ```bash
   uv run python start_mcp_http.py --port 8080
   ```
   
   **Option B: With Docker (API key required):**
   ```bash
   docker compose up
   # or
   task docker-dev
   ```

2. **Configure Cursor:**
   - Open Cursor Settings
   - Navigate to MCP/Model Context Protocol settings
   - Add the following configuration:
   
   **For local development (no API key):**
   ```json
   {
     "mcpServers": {
       "TIDAL MCP (HTTP)": {
         "url": "http://127.0.0.1:8080/sse",
         "transport": "sse"
       }
     }
   }
   ```
   
   **For Docker (with API key):**
   ```json
   {
     "mcpServers": {
       "TIDAL MCP (HTTP)": {
         "url": "http://127.0.0.1:8080/sse",
         "transport": "sse",
         "headers": {
           "x-api-key": "mcptest"
         }
       }
     }
   }
   ```

3. **Restart Cursor** and verify the connection

**Note:** When running locally without Docker, API key authentication is optional (only required if `API_KEY` environment variable is set). When using Docker Compose, the default dev API key `mcptest` is required.

For detailed instructions and troubleshooting, see the [HTTP Debug Setup Guide](docs/HTTP_DEBUG_SETUP.md).

#### Troubleshooting

**Server won't start:**
- Verify the `uv` path is correct: run `which uv` in terminal
- Verify the project path is correct and points to `mcp_server/server.py`
- Check that all dependencies are installed: `uv pip install --editable .`

**Port already in use:**
- Change `PORT` or `MCP_HTTP_PORT` to a different port (e.g., "9000")
- Make sure no other instance of the server is running

**Import errors:**
- Make sure you've installed dependencies: `uv pip install --editable .`
- Verify you're using the correct Python version (3.10+)

## Usage Examples

Once configured, you can interact with your TIDAL account through Claude by asking questions like:

### Getting Started
- *"Help me log in to TIDAL"*
- *"Show me my favorite tracks"*
- *"What playlists do I have?"*

### Recommendations
- *"Recommend songs like those in my 'Chill Vibes' playlist, but slower and more acoustic."*
- *"Create a playlist based on my top 20 favorite tracks, but focused on chill, late-night vibes."*
- *"Find songs similar to my favorites but from recent years (2020-2024)."*
- *"Recommend upbeat tracks similar to my current favorites."*

### Playlist Management
- *"Show me all the tracks in my 'Workout Mix' playlist"*
- *"Create a new playlist called 'Study Focus' with relaxing instrumental tracks"*
- *"Delete my 'Old Mix' playlist"*

### Search
- *"Search for tracks by Radiohead"*
- *"Find albums by D'Angelo"*
- *"Search for the artist 'Kendrick Lamar'"*

*💡 Tips:*
- Use more tracks as seeds to broaden recommendations
- Ask for more recommendations if you want a longer playlist
- You can combine search with recommendations for more targeted results
- Delete playlists anytime if you're not satisfied — no pressure!

## Available Tools

The TIDAL MCP integration provides the following tools:

### Authentication
- **`tidal_login()`**: Authenticate with TIDAL through OAuth2 browser login flow. Opens a browser window for secure authentication and stores the session for future use.

### Favorites & Recommendations
- **`get_favorite_tracks(limit: int = 20)`**: Retrieve your favorite tracks from your TIDAL account. Returns track information including ID, title, artist, album, duration, and TIDAL URLs.
- **`recommend_tracks(track_ids: list[str] | None = None, filter_criteria: str | None = None, limit_per_track: int = 20, limit_from_favorite: int = 20)`**: Get personalized music recommendations based on:
  - Your favorite tracks (if no track IDs provided)
  - Specific track IDs you provide
  - Optional filtering criteria (e.g., "relaxing", "recent releases", "upbeat", "jazz influences")
  - Returns seed tracks and recommended tracks with full metadata

### Playlist Management
- **`create_tidal_playlist(title: str, track_ids: list, description: str = "")`**: Create a new playlist in your TIDAL account with specified tracks. Returns playlist details including TIDAL URL.
- **`get_user_playlists()`**: List all your playlists on TIDAL, sorted by last updated date (most recent first). Returns playlist metadata including title, track count, and TIDAL URLs.
- **`get_playlist_tracks(playlist_id: str, limit: int = 100)`**: Retrieve all tracks from a specific playlist. Returns track information with full metadata.
- **`delete_tidal_playlist(playlist_id: str)`**: Delete a playlist from your TIDAL account by its ID.

### Search
- **`search_tidal(query: str, limit: int = 20, search_types: str | None = "tracks,albums,artists")`**: General search function that can search for tracks, albums, and/or artists. You can specify which types to search (e.g., "tracks", "albums,artists", or all three).
- **`search_tidal_tracks(query: str, limit: int = 20)`**: Search specifically for tracks. Returns matching tracks with full metadata and TIDAL URLs.
- **`search_tidal_albums(query: str, limit: int = 20)`**: Search specifically for albums. Returns matching albums with artist, release date, track count, and TIDAL URLs.
- **`search_tidal_artists(query: str, limit: int = 20)`**: Search specifically for artists. Returns matching artists with TIDAL URLs.

All search functions support up to 50 results per type and return TIDAL URLs for easy access to the content.

## License

[MIT License](LICENSE)

## Acknowledgements

- [Model Context Protocol (MCP)](https://github.com/modelcontextprotocol/python-sdk)
- [TIDAL Python API](https://github.com/tamland/python-tidal)