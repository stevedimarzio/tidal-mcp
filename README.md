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

- 🌟 **Music Recommendations**: Get personalized track recommendations based on your listening history **plus your custom criteria**.
- ၊၊||၊ **Playlist Management**: Create, view, and manage your TIDAL playlists

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
# Option 1: Using the start script
uv run python start_mcp.py

# Option 2: Using uv with mcp command directly
uv run mcp run mcp_server/server.py
```

**Note:** Always use `uv run` to ensure all dependencies are available in the correct environment.


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
      "env": {
        "TIDAL_MCP_PORT": "5050"
      },
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
- `"5050"` → Optional: Change the port if 5050 is already in use

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
      "env": {
        "TIDAL_MCP_PORT": "5050"
      },
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

#### Troubleshooting

**Server won't start:**
- Verify the `uv` path is correct: run `which uv` in terminal
- Verify the project path is correct and points to `mcp_server/server.py`
- Check that all dependencies are installed: `uv pip install --editable .`

**Port already in use:**
- Change `TIDAL_MCP_PORT` to a different port (e.g., "5100", "8080")
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
- **`tidal_login`**: Authenticate with TIDAL through browser login flow. Opens a browser window for OAuth authentication.

### Tracks & Recommendations
- **`get_favorite_tracks`**: Retrieve your favorite tracks from TIDAL account
- **`recommend_tracks`**: Get personalized music recommendations based on your favorites or specific track IDs. Supports filtering criteria.

### Playlist Management
- **`create_tidal_playlist`**: Create a new playlist in your TIDAL account with specified tracks
- **`get_user_playlists`**: List all your playlists on TIDAL (sorted by last updated)
- **`get_playlist_tracks`**: Retrieve all tracks from a specific playlist
- **`delete_tidal_playlist`**: Delete a playlist from your TIDAL account

### Search
- **`search_tidal`**: Search for tracks, albums, and/or artists on TIDAL
- **`search_tidal_tracks`**: Search specifically for tracks
- **`search_tidal_albums`**: Search specifically for albums
- **`search_tidal_artists`**: Search specifically for artists

## License

[MIT License](LICENSE)

## Acknowledgements

- [Model Context Protocol (MCP)](https://github.com/modelcontextprotocol/python-sdk)
- [TIDAL Python API](https://github.com/tamland/python-tidal)