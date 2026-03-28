# Security Notes

`android-shizuku-mcp` is intentionally optimized for low-friction command execution by an LLM running close to the device. It is not a hardened shell sandbox.

## What Is Actually Implemented

1. **Localhost-by-default bind**: the server starts on `127.0.0.1` by default.
2. **Optional bearer token**: requests can require `Authorization: Bearer <token>` when `MCP_AUTH_TOKEN` is set.
3. **Minimal shell denylist**: a small set of obviously destructive patterns is blocked.
4. **Environment isolation for `rish`**: `RISH_PRESERVE_ENV=0` is used for privileged shell execution.
5. **Runtime job retention**: job files are rotated and cleaned up to reduce stale runtime buildup.

## Important Non-Goals

1. **No strict shell sandbox**: the universal `shell` tool is designed to stay permissive.
2. **No strong command policy boundary**: the denylist reduces accidents, but shell access is still powerful.
3. **No claim of browser-grade Origin protection**: do not assume cross-origin protections that are not implemented in code.

## Operational Recommendations

1. Keep the server bound to localhost unless you have a very specific reason not to.
2. Set a bearer token if any other local client could reach the server.
3. Treat `rish` access as privileged device control.
4. Review saved stdout/stderr artifacts and runtime files if you are debugging odd agent behavior.
5. Only grant Termux and Shizuku the permissions you actually need.

## Known Limitations

1. A small-context LLM can still issue dangerous shell commands if prompted to do so.
2. Anyone with local access to the Termux home directory can inspect saved artifacts and runtime job files.
3. Shell output truncation and shaping improve usability, not security.
