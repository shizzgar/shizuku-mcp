# Termux Shell Patterns

## Low-context habits

- Ask for filenames before file contents.
- Ask for counts before full lists.
- Redirect noisy build output into files.
- Read failure tails before full logs.
- Prefer one persistent shell session for iterative work instead of reissuing separate commands.

## Good patterns

Resolve the rebuild helper once before switching into the apktool work directory:

```bash
REVERSE_HELPER="$(realpath skills/android-reverse-flow/scripts/apktool-build-termux.sh)"
```

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
"$REVERSE_HELPER" apktool-out build/app.apk > build/stdout.log 2> build/stderr.log
tail -n 60 build/stderr.log
```

Build a debuggable APK on-device:

```bash
"$REVERSE_HELPER" apktool-out build/app-debug.apk --debuggable
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
