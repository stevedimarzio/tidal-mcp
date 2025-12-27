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

To run the MCP server in HTTP mode:

```bash
uv run uvicorn app:app --host 127.0.0.1 --port 8080
```

**Note:** Always use `uv run` to ensure all dependencies are available in the correct environment.

The server will be available at `http://127.0.0.1:8080` (or configure with `--host` and `--port`). For production, use `--host 0.0.0.0` to accept connections from all interfaces.

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

**For cloud deployment (linux/amd64):**
For cloud platforms that require `linux/amd64` architecture, build with the correct platform:

```bash
docker buildx build --platform linux/amd64 -t tidal-mcp:latest .
```

Or use the task command:
```bash
task docker-build-cloud
```

**⚠️ Important:** If you're building on Apple Silicon (M1/M2/M3 Mac), you must specify `--platform linux/amd64` for cloud deployment, otherwise you'll get an "exec format error".

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
- Enable API key authentication with default dev key: `mcptest` (via `X-API-KEY` header)

To run in detached mode:

```bash
docker compose up -d
```

To stop the server:

```bash
docker compose down
```

**Option 2: Using Docker directly**

Run the container:

```bash
docker run -p 8080:8080 \
  -v $(pwd)/data/sessions:/app/data/sessions \
  tidal-mcp:latest
```

#### Environment Variables

You can customize the server behavior using environment variables:

- `PORT`: Port for the MCP HTTP server (default: `8080`)
- `HOST`: Host to bind to (default: `0.0.0.0` for Docker, `127.0.0.1` for local)
- `API_KEY`: API key for authentication via `X-API-KEY` header (default in docker-compose: `mcptest` for development, **change in production!**)

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
http://localhost:8080/mcp
```

**Note:** The Docker Compose setup uses API key authentication by default (dev key: `mcptest`). You must include the `X-API-KEY` header in your requests.

For Cursor configuration, use:

```json
{
  "mcpServers": {
    "TIDAL MCP (Docker)": {
      "url": "http://localhost:8080/mcp",
      "transport": "sse",
      "headers": {
        "X-API-KEY": "mcptest"
      }
    }
  }
}
```

**⚠️ Important:** The default API key `mcptest` is for **development only**. For production deployments, set a strong, unique API key via the `API_KEY` environment variable.

### Cloud Deployment

The container is designed to work with cloud container services. Here are deployment options:

#### FastMCP Cloud (Recommended)

FastMCP Cloud provides free hosting for personal MCP servers. To deploy:

1. **Install FastMCP CLI** (if not already installed):
   ```bash
   pip install fastmcp
   ```

2. **Login to FastMCP Cloud**:
   ```bash
   fastmcp cloud login
   ```

3. **Deploy your server**:
   ```bash
   fastmcp cloud deploy
   ```

4. **Set your API key** (for authentication):
   ```bash
   fastmcp cloud env set API_KEY=your-production-api-key-here
   ```

5. **Get your server URL**:
   ```bash
   fastmcp cloud status
   ```

6. **Configure your MCP client** to use the FastMCP Cloud URL:

```json
{
  "mcpServers": {
    "TIDAL MCP (FastMCP Cloud)": {
      "url": "https://your-server.fastmcp.cloud/mcp",
      "transport": "sse",
      "headers": {
        "X-API-KEY": "your-production-api-key-here"
      }
    }
  }
}
```

For more details, see the [FastMCP Cloud documentation](https://gofastmcp.com/).

#### Generic Cloud Container Services

The container can be deployed to any cloud container service (AWS ECS, Azure Container Apps, etc.):

**Key Configuration:**
- Set `API_KEY` environment variable for authentication
- Set `PORT=8080` (or let the service auto-detect)
- Expose port 8080
- The `/health` endpoint bypasses API key authentication for health checks

**Example for AWS ECS / Fargate:**

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

**Example for Azure Container Apps:**

```bash
az containerapp create \
  --name tidal-mcp \
  --resource-group your-resource-group \
  --image your-registry.azurecr.io/tidal-mcp:latest \
  --target-port 8080 \
  --env-vars API_KEY=your-production-api-key-here PORT=8080
```

**Security Best Practices:**
- Never commit API keys to version control
- Use different API keys for different environments (dev, staging, prod)
- Rotate API keys regularly
- Use your cloud provider's secret management service for sensitive values

## MCP Client Configuration

### Cursor Configuration (HTTP Mode for Debugging)

To use the MCP server with Cursor in HTTP mode for debugging:

1. **Start the server in HTTP mode:**
   
   **Option A: Local development (no API key required):**
   ```bash
   uv run uvicorn app:app --host 127.0.0.1 --port 8080
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
         "url": "http://127.0.0.1:8080/mcp",
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
        "url": "http://127.0.0.1:8080/mcp",
        "transport": "sse",
        "headers": {
          "X-API-KEY": "mcptest"
         }
       }
     }
   }
   ```

3. **Restart Cursor** and verify the connection

**Note:** When running locally without Docker, API key authentication is optional (only required if `API_KEY` environment variable is set). When using Docker Compose, the default dev API key `mcptest` is required.

For detailed instructions and troubleshooting, see the [HTTP Debug Setup Guide](docs/HTTP_DEBUG_SETUP.md).

### Mistral Configuration (Remote Server via Connectors)

To integrate a remote `tidal-mcp` server with Mistral AI using connectors, follow these steps:

#### Prerequisites

1. **Deploy your TIDAL MCP server** to a publicly accessible URL (e.g., FastMCP Cloud, ECS, Azure Container Apps, or any HTTPS endpoint)
2. **Note your server URL** - it should be in the format: `https://your-domain.com/mcp` or `https://your-server.fastmcp.cloud/mcp`
3. **Have your API key ready** - the API key you configured when deploying the server (via `API_KEY` environment variable)

#### Step 1: Access Connectors in Mistral

1. Open Mistral AI (le Chat)
2. Click the **toggle panel button** (☰) to reveal the side panel
3. Expand the **Intelligence** menu
4. Select **Connectors**

#### Step 2: Add Custom MCP Connector

1. Click the **+ Add Connector** button
2. Switch to the **Custom MCP Connector** tab

#### Step 3: Configure the Connector

Fill in the connector configuration with the following details:

- **Connector Name**: `TIDAL MCP` (or any name you prefer)
- **Connection Server**: Enter your full server URL with the `/mcp` endpoint:
  ```
  https://your-domain.com/mcp
  ```
  Or for FastMCP Cloud:
  ```
  https://your-server.fastmcp.cloud/mcp
  ```
- **Description** (optional): `TIDAL music integration for recommendations, playlists, and search`
- **Authentication Method**: Select **API Key** or **Custom Header** (depending on Mistral's options)
- **API Key Header**: `X-API-KEY`
- **API Key Value**: Your production API key (the one you set via `API_KEY` environment variable)

**Example Configuration:**

If Mistral uses a JSON configuration format, use:

```json
{
  "name": "TIDAL MCP",
  "url": "https://your-server.fastmcp.cloud/mcp",
  "transport": "sse",
  "headers": {
    "X-API-KEY": "your-production-api-key-here"
  }
}
```

#### Step 4: Connect and Verify

1. Click the **Connect** button
2. Wait for Mistral to establish the connection
3. Verify the connection status shows as **Connected** or **Active**

#### Step 5: Use the Connector in Conversations

1. Start a new conversation in Mistral
2. Click the **Tools** button below the input box
3. Under the **Connectors** section, ensure **TIDAL MCP** is selected/enabled
4. You can now ask questions like:
   - *"Help me log in to TIDAL"*
   - *"Show me my favorite tracks"*
   - *"Recommend songs similar to my favorites"*

#### Troubleshooting

**Connection fails:**
- Verify your server URL is correct and includes `/mcp` endpoint
- Ensure your server is publicly accessible (not behind a firewall)
- Check that your API key matches the one configured on the server
- Verify the server is running and responding to health checks: `curl https://your-domain.com/health`

**"Request validation failed" error:**
- This error typically occurs when uvicorn's proxy headers middleware isn't configured to trust the proxy
- The Docker image is configured with `--forwarded-allow-ips='*'` by default to handle proxy headers
- If you're still experiencing this error, ensure you're using the latest Docker image version
- You can override the forwarded IPs configuration via the `FORWARDED_ALLOW_IPS` environment variable if needed

**Authentication errors:**
- Double-check the API key header name is exactly `X-API-KEY` (case-insensitive, but use uppercase for consistency)
- Verify the API key value matches your server's `API_KEY` environment variable
- Ensure your server has API key authentication enabled (set `API_KEY` environment variable)

**Tools not appearing:**
- Make sure the connector is enabled in the Tools menu for your conversation
- Try disconnecting and reconnecting the connector
- Check Mistral's connector logs for any error messages

**Server not responding:**
- Verify your server is deployed and running
- Check cloud service logs for errors
- Test the `/health` endpoint directly: `curl https://your-domain.com/health`
- Ensure your server supports SSE (Server-Sent Events) transport

#### Security Best Practices

- **Use HTTPS**: Always use HTTPS URLs for remote connections (never HTTP)
- **Strong API Keys**: Use a strong, unique API key for production (not the default `mcptest`)
- **Rotate Keys**: Regularly rotate your API keys for security
- **Monitor Access**: Review your server logs to monitor connector usage
- **Restrict Access**: Consider IP whitelisting if your cloud provider supports it

#### Example: FastMCP Cloud Deployment for Mistral

If deploying to FastMCP Cloud for Mistral:

```bash
# Deploy with FastMCP Cloud
fastmcp cloud deploy

# Set your production API key
fastmcp cloud env set API_KEY=your-secure-production-key-here

# Get your server URL
fastmcp cloud status
```

Then use the FastMCP Cloud URL in Mistral:
```
https://your-server.fastmcp.cloud/mcp
```

## Usage Examples

Once configured, you can interact with your TIDAL account by asking questions like:

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