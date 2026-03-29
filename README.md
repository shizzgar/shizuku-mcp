# android-shizuku-mcp

An open-source Model Context Protocol (MCP) server for Android, running in Termux. It allows LLM agents to control your Android device securely via Shizuku (`rish`) and Termux:API.

## Features

* **Streamable HTTP Transport**: Modern MCP transport for robust communication.
* **Single Universal Shell Tool**: One MCP tool for Termux and `rish`, designed to feel closer to a real terminal.
* **Hybrid Exec + Session Model**: The same `shell` tool supports one-shot commands and persistent shell sessions.
* **Raw Inline First**: If stdout/stderr fit the budget, they are returned whole instead of being split into preview sections.
* **Long-Running Recovery**: One-shot commands can still be polled/cancelled when they outlive the sync budget.
* **Interactive Session Flow**: Sessions support write/read/close on a persistent shell cursor.
* **Shizuku Integration**: High-privilege Android commands can be routed through `rish`.
* **Low-Context UX**: Error payloads stay short and operational for weak LLMs.
* **Artifact Management**: Command/session output is persisted for follow-up inspection when needed.

## Prerequisites

1. **Termux**: Install from F-Droid.
2. **Termux:API**: Install both the app (F-Droid) and the package (`pkg install termux-api`).
3. **Shizuku**: Set up on your device (Wireless Debugging or Root).
4. **rish**: Copy `rish` to your Termux home directory (`~/bin/rish`) and ensure it's executable and not writable by others (on Android 14+).

## Installation

1. Clone this repository in Termux.
2. Run the installation script:
   ```bash
   ./install.sh
   ```
3. Copy the Bearer token from the `.env` file created.

## Usage

Start the server:
```bash
./run-server.sh
```

By default, the server runs on `http://127.0.0.1:8765/mcp`.

### Connecting an MCP Client

Use the following configuration (e.g., in Claude Desktop):

```json
{
  "mcpServers": {
    "android": {
      "command": "python",
      "args": ["/path/to/android-shizuku-mcp/src/main.py"],
      "env": {
        "MCP_AUTH_TOKEN": "your-token-here"
      }
    }
  }
}
```

Or connect via HTTP directly using an MCP client supporting Streamable HTTP.

## Available Tools

* **Shell**: `shell` is the primary universal tool. It supports `exec`, `poll`, `open_session`, `write`, `read`, `close`, and `cancel`.
* **System**: `doctor`
* **Artifacts**: `list_artifacts`

## Autostart

Run `./setup_boot.sh` to create a Termux:Boot script. Ensure the Termux:Boot app is installed.

## Security

* Bind to `127.0.0.1` unless you intentionally expose the server another way.
* Bearer token authentication is supported and recommended.
* The shell path is permissive by design and is not a command-policy sandbox.
* The server is optimized for low-friction command execution and low-context responses, not strict shell filtering.

## License

Apache-2.0
