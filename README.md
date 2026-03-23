# android-shizuku-mcp

An open-source Model Context Protocol (MCP) server for Android, running in Termux. It allows LLM agents to control your Android device securely via Shizuku (`rish`) and Termux:API.

## Features

* **Streamable HTTP Transport**: Modern MCP transport for robust communication.
* **Shizuku Integration**: High-privilege access for app management, intent launching, and screen operations.
* **Termux:API Integration**: Low-privilege access for clipboard, battery, wifi, and notifications.
* **Security-focused**: Localhost binding, Bearer token auth, and Origin checks.
* **Artifact Management**: Screenshot and screen recording capture.

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

* **System**: `doctor`, `ping`, `device_info`, `battery_status`, `wifi_status`.
* **Apps**: `list_packages`, `open_app`, `force_stop`.
* **Intents**: `start_intent`, `open_url`.
* **Screen**: `take_screenshot`, `record_screen`.
* **Utility**: `clipboard_get`, `clipboard_set`, `show_notification`.
* **Shell**: `shell_readonly`, `shell_privileged` (disabled by default).
* **Artifacts**: `list_artifacts`.

## Autostart

Run `./setup_boot.sh` to create a Termux:Boot script. Ensure the Termux:Boot app is installed.

## Security

* Bind only to `127.0.0.1`.
* Bearer token authentication (optional but recommended).
* Whitelist and blacklist for shell commands.
* Explicit confirmation required for privileged shell actions.

## License

Apache-2.0
