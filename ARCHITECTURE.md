# Architecture

`android-shizuku-mcp` is a Termux-hosted MCP server built around one main universal shell tool.

## Core Components

1. **MCP layer**
   `src/android_mcp/server.py` exposes the Streamable HTTP server, bearer-token middleware, and the public tools.

2. **Primary shell tool**
   `src/tools/shell_tools.py` is the main LLM-facing control surface.
   It validates shell arguments, chooses `termux` or `rish`, routes between one-shot exec and persistent sessions, and returns compact terminal-like results.

3. **Execution runners**
   `src/runners/subprocess_runner.py` handles subprocess creation, spool files, job persistence, PTY-backed sessions, incremental reads, cancellations, and runtime cleanup.
   `src/runners/rish_runner.py` handles privileged execution through `rish`.
   `src/runners/termux_api_runner.py` handles `termux-api` binaries.

4. **Health and artifacts**
   `src/doctor.py` reports environment health and runtime job statistics.
   `src/artifacts.py` manages saved artifacts and metadata.

## Execution Flow

1. A client calls the `shell` MCP tool.
2. The shell layer validates the request and selects a backend: local Termux shell or `rish`.
3. One-shot commands use the job runner; interactive flows use a persistent shell session.
4. Output is returned raw inline when it fits the budget. Truncation only happens when the budget is actually exceeded.
5. Follow-up calls poll jobs or write/read/close the same session without forcing the client to manually reconstruct terminal state.

## Design Priorities

1. **One dominant tool** instead of a wide MCP surface.
2. **Low-context responses** for weak or small-window LLMs.
3. **Permissive execution** over command filtering.
4. **Terminal-like interaction** through persistent sessions when needed.
