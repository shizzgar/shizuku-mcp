# Termux Shell Patterns

## Low-context habits

- Ask for filenames before file contents.
- Ask for counts before full lists.
- Redirect noisy build output into files.
- Read failure tails before full logs.
- Use `job_id` and offsets for long-running tasks.

## Good patterns

List candidate files:

```bash
find apktool-out -type f | rg 'AndroidManifest|strings|public|smali.*/Target'
```

Read a focused slice:

```bash
sed -n '80,160p' apktool-out/AndroidManifest.xml
```

Capture noisy output:

```bash
apktool b apktool-out -o build/app.apk > build/stdout.log 2> build/stderr.log
tail -n 60 build/stderr.log
```

Summarize trees instead of dumping them:

```bash
find apktool-out/res -maxdepth 2 -type f | wc -l
find apktool-out/res -maxdepth 2 -type f | head -n 40
```

Prefer grep-first for crash or build errors:

```bash
rg -n "error:|Exception|FATAL|AndroidRuntime|INSTALL_FAILED" build *.log
```
