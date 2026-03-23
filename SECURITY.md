# Security Policy

`android-shizuku-mcp` is designed to be as secure as possible while providing powerful device control.

## Implemented Protections

1.  **Local Bind Only**: The server is bound to `127.0.0.1` by default, making it inaccessible from other devices on the same network.
2.  **Bearer Token Authentication**: All requests require a valid `Authorization: Bearer <token>` header if `MCP_AUTH_TOKEN` is set.
3.  **Origin Check**: Basic protection against DNS rebinding and cross-origin requests from the browser.
4.  **Shell Filtering**:
    *   **Blacklist**: Commands like `rm -rf /`, `su`, `sudo`, `reboot` are explicitly blocked.
    *   **Whitelist**: `shell_readonly` only allows specific safe patterns.
    *   **Explicit Confirmation**: `shell_privileged` requires a `confirm_dangerous=true` argument and is disabled by default.
5.  **Environment Isolation**: `RISH_PRESERVE_ENV=0` is used to prevent Termux environment leakage into the high-privilege shell.
6.  **Android 14+ Protections**: Automated warnings for writable `rish` files, which are a security risk on newer Android versions.

## Recommendations

1.  **Use a strong token**: The default `install.sh` generates a random 16-character hex token. Keep it secret.
2.  **Keep Shizuku updated**: Newer versions of Shizuku have better security fixes.
3.  **Audit Logs**: Regularly check the `logs/` directory for any unusual tool calls.
4.  **Restrict Termux Permissions**: Only grant the permissions strictly necessary for your use case (e.g., storage, if needed).

## Known Limitations

*   **ADB-mode Shizuku**: While ADB is powerful, it is less secure than root as it bypasses some Android security features.
*   **Shell Redirection**: Even with blacklists, shell access via `rish` is inherently powerful. Disable `enable_raw_shell` if you don't need it.
*   **Artifact Exposure**: Anyone with local access to the Termux home directory can read the screenshots and recordings.
