# Architecture

`android-shizuku-mcp` is a modular MCP server designed for Android environments, specifically Termux.

## Core Components

1.  **MCP Layer (`src/mcp/`)**:
    *   Uses `FastMCP` (higher level) but with a custom Starlette wrapper for security middleware.
    *   Exposes tools via the MCP protocol.
    *   Supports Streamable HTTP transport.

2.  **Tool Registry (`src/tools/`)**:
    *   Groups tools by functional areas: `doctor`, `apps`, `intents`, `screen`, `utility`, `shell`.
    *   Tools are asynchronous and handle error mapping to `MCPError`.

3.  **Runners (`src/runners/`)**:
    *   **Subprocess Runner**: Low-level `asyncio.create_subprocess_exec` wrapper with timeout and capture.
    *   **Rish Runner**: Handles Shizuku/rish execution, environment variables (`RISH_PRESERVE_ENV`), and path discovery.
    *   **Termux API Runner**: Handles interactions with the `termux-api` commands.

4.  **Health Module (`src/doctor.py`)**:
    *   Aggregates system status, tool availability, and security warnings.

5.  **Artifacts Module (`src/artifacts.py`)**:
    *   Manages file-based outputs (screenshots, recordings) within a dedicated directory.

## Execution Flow

1.  Client connects via HTTP to `http://127.0.0.1:8765/mcp`.
2.  Security middleware validates Bearer token and Origin.
3.  FastMCP routes tool calls to the corresponding tool function.
4.  Tool function invokes a Runner (Subprocess/Rish/Termux API).
5.  Runner executes the command on Android and returns structured result.
6.  Result is JSON-serialized and returned to the client.

## Security Boundaries

*   **Safe Tools**: Native Python or `termux-api` actions.
*   **Privileged Tools**: Actions requiring `rish` (app management, intents, screen capture).
*   **Dangerous Tools**: Raw shell access via `rish` (disabled by default, requires whitelist and confirmation).
