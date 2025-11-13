# Setting Up TIDAL MCP Server in HTTP Mode for Debugging

This guide explains how to start the TIDAL MCP server in HTTP mode and connect it to Cursor for debugging.

## Why HTTP Mode?

HTTP mode allows you to:
- Debug the MCP server using standard HTTP debugging tools
- Monitor network traffic and requests
- Connect Cursor to the server via HTTP transport
- Use browser-based debugging tools
- Easily restart the server without restarting Cursor

## Starting the Server in HTTP Mode

### Option 1: Using the HTTP Startup Script

```bash
# Start the server on the default port (8100)
uv run python start_mcp_http.py

# Or specify a custom port
uv run python start_mcp_http.py --port 8100

# Or specify both host and port
uv run python start_mcp_http.py --host 127.0.0.1 --port 8100
```

### Option 2: Using Environment Variables

```bash
# Set the MCP HTTP port
export MCP_HTTP_PORT=8100

# Set the FastAPI backend port (if different from default 5050)
export TIDAL_MCP_PORT=5050

# Start the server
uv run python start_mcp_http.py
```

### Verifying the Server is Running

Once started, you should see output like:
```
Starting TIDAL MCP server in HTTP mode on 127.0.0.1:8100...
FastAPI backend will run on port 5050
Connect Cursor to: http://127.0.0.1:8100/sse
Press Ctrl+C to stop the server
```

You can also verify by visiting `http://127.0.0.1:8100/health` in your browser or using curl:
```bash
curl http://127.0.0.1:8100/health
```

## Configuring Cursor for HTTP Mode

### Step 1: Locate Cursor's MCP Configuration

The configuration file location depends on your operating system:

- **macOS**: `~/Library/Application Support/Cursor/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json`
- **Windows**: `%APPDATA%\Cursor\User\globalStorage\rooveterinaryinc.roo-cline\settings\cline_mcp_settings.json`
- **Linux**: `~/.config/Cursor/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json`

Alternatively, you can access it through Cursor:
1. Open Cursor Settings (Cmd/Ctrl + ,)
2. Search for "MCP" or "Model Context Protocol"
3. Look for MCP server configuration options

### Step 2: Add HTTP Server Configuration

Add the following configuration to your Cursor MCP settings:

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

**Note**: The exact format may vary depending on Cursor's MCP implementation. Some versions may use:
- `"type": "sse"` instead of `"transport": "sse"`
- `"endpoint": "http://127.0.0.1:8100/sse"` instead of `"url"`

### Step 3: Alternative Configuration Format

If the above doesn't work, try this format:

```json
{
  "mcpServers": {
    "TIDAL MCP (HTTP)": {
      "command": "curl",
      "args": [
        "-N",
        "-H", "Accept: text/event-stream",
        "http://127.0.0.1:8100/sse"
      ],
      "transport": "sse"
    }
  }
}
```

Or if Cursor supports direct HTTP configuration:

```json
{
  "mcpServers": {
    "TIDAL MCP (HTTP)": {
      "type": "http",
      "url": "http://127.0.0.1:8100",
      "path": "/sse"
    }
  }
}
```

### Step 4: Restart Cursor

After updating the configuration:
1. Save the configuration file
2. Completely quit and restart Cursor
3. The MCP server should now connect via HTTP

## Troubleshooting

### Server Won't Start

**Problem**: Port already in use
```bash
Error: [Errno 48] Address already in use
```

**Solution**: Use a different port
```bash
uv run python start_mcp_http.py --port 8101
```
Then update the Cursor configuration to use the new port.

### Cursor Can't Connect

**Problem**: Connection refused or timeout

**Solutions**:
1. Verify the server is running:
   ```bash
   curl http://127.0.0.1:8100/health
   ```

2. Check the port in the configuration matches the server port

3. Ensure the server is bound to `127.0.0.1` (not `localhost` or `0.0.0.0`)

4. Check firewall settings if using a different host

### SSE Endpoint Not Found

**Problem**: 404 error when accessing `/sse`

**Solution**: Verify the FastMCP server is using SSE transport. The endpoint should be automatically created by `mcp.sse_app()`.

### FastAPI Backend Not Starting

**Problem**: MCP server starts but FastAPI backend doesn't

**Solution**: Check the logs for FastAPI startup errors. The FastAPI app runs on a separate port (default 5050) and is started automatically when the MCP server module loads.

## Testing the Connection

Once configured, you can test the connection in Cursor:

1. Open a new chat in Cursor
2. Ask: "Can you help me log in to TIDAL?"
3. The MCP tools should be available and working

## Debugging Tips

### Monitor HTTP Traffic

You can monitor the HTTP traffic between Cursor and the MCP server using:

```bash
# Using netcat to see raw traffic
nc -l 8100

# Or use a proxy like mitmproxy
mitmproxy -p 8100
```

### View Server Logs

The server logs will show:
- Incoming requests
- Tool calls
- Responses
- Errors

### Use Browser DevTools

If you're testing the SSE endpoint directly, you can use browser DevTools:
1. Open `http://127.0.0.1:8100/sse` in your browser
2. Open DevTools (F12)
3. Check the Network tab for SSE events

## Switching Back to Stdio Mode

To switch back to stdio mode (for production use with Claude Desktop):

1. Stop the HTTP server (Ctrl+C)
2. Update Cursor configuration to use stdio:
   ```json
   {
     "mcpServers": {
       "TIDAL MCP": {
         "command": "/opt/homebrew/bin/uv",
         "args": [
           "run",
           "python",
           "/path/to/tidal-mcp/start_mcp.py"
         ]
       }
     }
   }
   ```
3. Restart Cursor

## Additional Resources

- [MCP Protocol Documentation](https://modelcontextprotocol.io)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Cursor MCP Integration](https://cursor.sh/docs/mcp)

