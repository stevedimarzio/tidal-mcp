# TIDAL MCP 🌟🎧

Standalone MCP server for integrating TIDAL services with compatible LLMs (Claude, Mistral, Cursor, etc.).

Built with **FastMCP 3.0**, this server provides a robust integration with TIDAL's API, allowing your AI assistant to manage your music library, discover new tracks, and create personalized playlists.

## 🚀 Features

- 🔐 **OAuth2 Authentication**: Secure browser-based login flow with session persistence.
- 🌟 **Music Recommendations**: Personalized track suggestions based on your favorites or specific seeds.
- 📋 **Playlist Management**: Create, view, browse, and delete TIDAL playlists directly from your chat.
- 🔍 **Music Search**: Comprehensive search for tracks, albums, and artists in TIDAL's vast catalog.
- ❤️ **Favorites Access**: Quick access to your favorite tracks and artists.
- 🎵 **Genre Exploration**: Browse and explore TIDAL genres for targeted discovery.
- 🛡️ **API Security**: Optional `X-API-KEY` header validation for secure remote access.
- ⚡ **HTTP/SSE Transport**: High-performance transport layer via ASGI (Uvicorn).

## 🛠️ Prerequisites

- **Python 3.10+**
- **[uv](https://github.com/astral-sh/uv)** (highly recommended Python package manager)
- **TIDAL Subscription** (required for API access)

## 📥 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yuhuacheng/tidal-mcp.git
   cd tidal-mcp
   ```

2. **Install dependencies:**
   ```bash
   uv pip install --editable .
   ```

## 🏃 Running Locally

To run the TIDAL MCP server in HTTP mode:

```bash
export API_KEY=your_secret_key  # Optional: Protects your server
uv run fastmcp run mcp_server/server.py --host 127.0.0.1 --port 8080 --transport http
```

The server will be available at `http://127.0.0.1:8080/mcp`.

## 🤖 MCP Client Configuration

### Claude Desktop (Mac)

To integrate with Claude Desktop, add the following to your configuration file (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "tidal": {
      "command": "uv",
      "args": [
        "run",
        "--with", "fastmcp",
        "fastmcp", "run",
        "mcp_server/server.py",
        "--host", "127.0.0.1",
        "--port", "8080",
        "--transport", "http"
      ],
      "env": {
        "API_KEY": "your_secret_key",
        "TIDAL_USER_ID": "your_default_user_name"
      }
    }
  }
}
```

### Mistral AI (Le Chat)

TIDAL MCP works seamlessly with Mistral's Custom MCP Connectors:

1. **Expose your server**: Use a tool like `ngrok` or deploy to a cloud provider to get a public HTTPS URL.
2. **Add Connector**:
   - Go to **Mistral AI > Intelligence > Connectors**.
   - Click **+ Add Connector** and select **Custom MCP Connector**.
   - **Name**: `TIDAL`
   - **URL**: `https://your-public-domain.com/mcp`
   - **Headers**: Add `X-API-KEY: your_secret_key` if configured.
3. **Connect**: Click connect and verify the status is **Active**.

### Cursor

Add a new MCP server in Cursor settings:
- **Type**: `SSE`
- **URL**: `http://127.0.0.1:8080/mcp`

## ⚙️ Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_KEY` | Secret key for `X-API-KEY` header validation. | None (disabled) |
| `TIDAL_USER_ID` | Default session ID/username to use for authentication. | None |
| `TIDAL_STORAGE_ENCRYPTION_KEY` | Key used to encrypt stored session data. | None |
| `PORT` | Port for the HTTP server. | 8080 |

## 🛠️ Available Tools

### Authentication
- `tidal_login`: Start the TIDAL OAuth2 flow. Returns a URL for browser login.
- `check_login_status`: Verify if the authentication process is complete.
- `list_tidal_sessions`: List all stored authentication sessions.
- `get_tidal_session_info`: Get details about a specific session.

### Music Discovery & Library
- `get_favorite_tracks`: Retrieve your favorite tracks.
- `recommend_tracks`: Get personalized recommendations (minimum 20 tracks suggested).
- `explore_tidal_genres`: Browse available music genres on TIDAL.

### Search
- `search_tidal`: Search for tracks, albums, and artists.
- `search_tidal_tracks`: Search specifically for tracks.
- `search_tidal_albums`: Search specifically for albums.
- `search_tidal_artists`: Search specifically for artists.

### Playlist Management
- `create_tidal_playlist`: Create a new playlist with specific tracks.
- `get_user_playlists`: List all your TIDAL playlists.
- `get_playlist_tracks`: Get all tracks from a specific playlist.
- `delete_tidal_playlist`: Delete a playlist from your account.

## 📝 Multi-User Support

The server supports multiple concurrent users via `session_id`. Each user's authentication state is stored securely in `~/.tidal-mcp/sessions`. When using in a multi-user environment, ensure `TIDAL_STORAGE_ENCRYPTION_KEY` is set to protect user tokens.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.