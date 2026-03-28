# Architecture

`android-shizuku-mcp` is a Termux-hosted MCP server built around one main universal shell tool.

## Core Components

1. **MCP layer**
   `src/android_mcp/server.py` exposes the Streamable HTTP server, bearer-token middleware, and the public tools.

2. **Primary shell tool**
   `src/tools/shell_tools.py` is the main LLM-facing control surface.
   It validates shell arguments, chooses `termux` or `rish`, starts or resumes jobs, and returns compact structured results.

3. **Execution runners**
   `src/runners/subprocess_runner.py` handles subprocess creation, spool files, job persistence, output shaping, offsets, cancellations, and runtime cleanup.
   `src/runners/rish_runner.py` handles privileged execution through `rish`.
   `src/runners/termux_api_runner.py` handles `termux-api` binaries.

4. **Health and artifacts**
   `src/doctor.py` reports environment health and runtime job statistics.
   `src/artifacts.py` manages saved artifacts and metadata.

## Execution Flow

1. A client calls the `shell` MCP tool.
2. The shell layer validates the request and selects a backend: local Termux shell or `rish`.
3. The subprocess runner starts a job and streams stdout/stderr into spool files.
4. The shell layer returns a compact response:
   `json`, `lines`, `text`, or `empty` preview shape,
   offsets for incremental reads,
   job state and finish reason when available.
5. Follow-up calls continue, cancel, or inspect the same job without needing large inline output.

## Design Priorities

1. **One dominant tool** instead of a wide MCP surface.
2. **Low-context responses** for weak or small-window LLMs.
3. **Permissive execution** over heavy command policy.
4. **Recoverable long-running work** through jobs, offsets, and resumable responses.
