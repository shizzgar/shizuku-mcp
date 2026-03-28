---
name: android-reverse-flow
description: Use when reverse-engineering Android APKs on-device in Termux/Shizuku, including unpacking with apktool, inspecting with jadx/smali, patching manifests/resources/code, rebuilding, signing, installing, and iterating with the MCP shell.
---

# Android Reverse Flow

Use this skill for end-to-end Android APK reversing on the phone.

## Quick rules

- Use the MCP `shell` tool as the main control surface.
- Keep shell output narrow. Prefer redirects, `rg`, `sed -n`, `jq`, `head`, and `tail` over dumping full trees or files.
- For long jobs, keep using the same `job_id` and offsets instead of restarting commands.
- On Android/Termux, treat plain `apktool b ...` as an anti-pattern. Always force `--aapt /data/data/com.termux/files/usr/bin/aapt2`.
- Prefer separate working directories per APK and per iteration.
- Treat `apktool` output as the editable source of truth for resources/manifest/smali. Treat `jadx` output as read-mostly navigation.

## Standard flow

1. Verify toolchain and environment first.
2. Copy the target APK into a disposable work directory.
3. Decode once with `apktool d`.
4. Inspect Java/Kotlin structure with `jadx` or `jadx-cli`.
5. Patch the smallest layer possible:
   manifest/resource first if enough;
   smali only if resource-level patching is not enough.
6. Rebuild with the helper script or `apktool b --aapt ...`.
7. Sign the rebuilt APK.
8. Install, launch, and capture failures.
9. Iterate from the exact failing step instead of re-running the full chain.

## Shell usage patterns

- Before reading big directories, ask for counts or filtered paths.
- Before reading large XML or smali files, pull only relevant slices with `rg -n` and `sed -n`.
- When a build command is noisy, redirect stdout/stderr to files and inspect the tail first.
- If a command hangs or takes time, let it run as a job and continue with offsets.

## When to read references

- Read [references/reverse-workflow.md](references/reverse-workflow.md) for the concrete decode -> patch -> rebuild -> sign -> install loop.
- Read [references/termux-shell-patterns.md](references/termux-shell-patterns.md) for low-context shell habits and command templates.
- If rebuild fails around `apktool`, resources, or `aapt2`, use the separate `apktool-termux-troubleshooting` skill.

## Preferred helper

- Prefer [scripts/apktool-build-termux.sh](scripts/apktool-build-termux.sh) for rebuilds on the phone instead of rewriting the full `apktool b ... --aapt ...` command each time.
