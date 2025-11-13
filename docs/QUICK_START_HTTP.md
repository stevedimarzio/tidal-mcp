# Quick Start: HTTP Mode for Cursor Debugging

## 1. Start the Server

```bash
uv run python start_mcp_http.py --port 8100
```

You should see:
```
Starting TIDAL MCP server in HTTP mode on 127.0.0.1:8100...
Connect Cursor to: http://127.0.0.1:8100/sse
```

## 2. Configure Cursor

Add to Cursor's MCP settings (location varies by OS, check Cursor Settings → MCP):

```json
{
  "mcpServers": {
    "TIDAL MCP (HTTP)": {
      "url": "http://127.0.0.1:8100/sse",
      "transport": "sse"
    }
  }
}
```

## 3. Restart Cursor

Quit and restart Cursor completely.

## 4. Test

In Cursor, ask: "Can you help me log in to TIDAL?"

---

**Full documentation:** See [docs/HTTP_DEBUG_SETUP.md](docs/HTTP_DEBUG_SETUP.md) for detailed instructions and troubleshooting.

