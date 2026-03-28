---
name: apktool-termux-troubleshooting
description: Use when apktool rebuilds fail on Android/Termux, especially around aapt2, resource compilation, signing, install failures, or shell-specific rebuild issues on-device.
---

# Apktool Termux Troubleshooting

Use this skill when the reverse workflow is blocked by rebuild, packaging, signing, or install failures.

## Fast triage order

1. Confirm which binaries are actually used: `apktool`, `aapt2`, `java`, `apksigner`.
2. Re-run the failing step with stderr redirected to a file.
3. Read the tail of stderr first, not the whole log.
4. Only after that inspect the specific resource, manifest, or smali file named in the error.

## Immediate checks

- `which apktool`
- `apktool --version`
- `which aapt2`
- `aapt2 version`
- `java -version`

## High-value rules

- For apktool 3.x, use `--aapt`, not `-a`.
- If the reverse-flow helper script is available, prefer it over retyping the full Termux rebuild command.
- If `aapt2` works directly but apktool still fails, verify what apktool actually invokes before blaming the binary.
- Resource compile errors are usually local to one XML/file name/value, not the whole project.
- Keep build logs in files and inspect them incrementally.

## When to read references

- Read [references/common-failures.md](references/common-failures.md) for failure signatures and the first commands to run.
- Read [references/rebuild-loop.md](references/rebuild-loop.md) for the shortest practical rebuild/sign/install/debug loop on Termux.
