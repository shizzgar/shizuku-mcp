# android-shizuku-mcp

An open-source Model Context Protocol (MCP) server for Android, running in Termux. It allows LLM agents to control your Android device securely via Shizuku (`rish`) and Termux:API.

## Features

* **Streamable HTTP Transport**: Modern MCP transport for robust communication.
* **Single Universal Shell Tool**: One MCP tool for Termux and `rish`, designed for small-context LLMs.
* **Adaptive Output Sampling**: Large output is stored on disk and returned as head/middle/tail previews.
* **Long-Running Job Continuations**: Commands that exceed the sync budget return a `job_id` instead of hard-failing.
* **Incremental Output Reads**: Follow-up calls can continue from `stdout`/`stderr` byte offsets.
* **Job Control**: Running jobs can be cancelled through the same `shell` tool.
* **Shizuku Integration**: High-privilege Android commands can be routed through `rish`.
* **Security-focused**: Localhost binding, Bearer token auth, and Origin checks.
* **Artifact Management**: Command stdout/stderr are persisted for follow-up inspection.

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

* **Shell**: `shell` is the primary universal tool. It can start commands, continue long-running jobs via `job_id`, cancel jobs, and return compact previews or incremental output slices via offsets.
* **System**: `doctor`
* **Artifacts**: `list_artifacts`

## Autostart

Run `./setup_boot.sh` to create a Termux:Boot script. Ensure the Termux:Boot app is installed.

## Security

* Bind only to `127.0.0.1`.
* Bearer token authentication (optional but recommended).
* Explicit denylist for obviously destructive shell commands.
* Large outputs are sampled to protect LLM context windows.

## License

Apache-2.0
