# Reverse Workflow

## 1. Prepare a workspace

Use a dedicated directory per target:

```bash
mkdir -p work/target-1
cp app.apk work/target-1/
REVERSE_HELPER="$(realpath skills/android-reverse-flow/scripts/apktool-build-termux.sh)"
cd work/target-1
```

Check the basic toolchain before doing expensive work:

```bash
which apktool jadx jadx-cli apksigner keytool java
apktool --version
java -version
test -x /data/data/com.termux/files/usr/bin/aapt2
```

If you are not starting from the MCP repo root, resolve `REVERSE_HELPER` to the absolute helper path once before changing directories.

## 2. Decode and inspect

Decode editable sources:

```bash
apktool d -f app.apk -o apktool-out
```

Decompile for navigation:

```bash
jadx -d jadx-out app.apk
```

When searching:

```bash
rg -n "target_string|target_class|target_permission" apktool-out jadx-out
find apktool-out -maxdepth 3 -type f | head -n 50
```

## 3. Patch in the smallest layer

Prefer this order:

1. `AndroidManifest.xml`
2. `res/values/*.xml`, layouts, drawables
3. selected smali files

Before editing a big file, preview only the needed slice:

```bash
rg -n "SomeMethod|const-string|android:exported" apktool-out
sed -n '120,220p' apktool-out/smali_classes2/.../Target.smali
```

## 4. Rebuild

On Android/Termux, do not use plain `apktool b ...`. Always force the Termux `aapt2` binary, or use the helper script.

Preferred rebuild:

```bash
"$REVERSE_HELPER" apktool-out build/app-unsigned.apk
```

Equivalent explicit command:

```bash
apktool b apktool-out --aapt /data/data/com.termux/files/usr/bin/aapt2 -o build/app-unsigned.apk
```

If `apktool` fails, keep the full error in a file and inspect the tail first:

```bash
"$REVERSE_HELPER" apktool-out build/app-unsigned.apk > build/apktool.stdout.log 2> build/apktool.stderr.log
tail -n 80 build/apktool.stderr.log
```

If you need a debuggable build:

```bash
"$REVERSE_HELPER" apktool-out build/app-unsigned.apk --debuggable
```

## 5. Sign

Common local keystore flow:

```bash
keytool -genkeypair -v -keystore debug.keystore -alias debug -keyalg RSA -keysize 2048 -validity 10000
apksigner sign --ks debug.keystore --out build/app-signed.apk build/app-unsigned.apk
apksigner verify -v build/app-signed.apk
```

## 6. Install and validate

Use regular Android install first; use `rish` when shell privileges are needed:

```bash
adb install -r build/app-signed.apk
```

On-device/privileged patterns:

```bash
pm install -r /sdcard/Download/app-signed.apk
monkey -p com.example.target -c android.intent.category.LAUNCHER 1
logcat | rg "FATAL EXCEPTION|AndroidRuntime|PackageManager"
```

## 7. Iterate intelligently

- If rebuild fails, do not re-run `jadx`.
- If stderr mentions `aapt2_*.tmp` plus `Syntax error: "(" unexpected`, rerun with the Termux `aapt2` path instead of the internal apktool temp binary.
- If stderr mentions `invalid entry name '$...`, inspect `res/` for filenames starting with `$` and XML refs like `@drawable/$...`.
- If install fails, inspect signing and package/version mismatch first.
- If launch fails, inspect `logcat` around the crash first.
- Save per-iteration logs so the next command only reads the delta.
