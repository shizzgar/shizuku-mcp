# Common Failures

## `Syntax error: "(" unexpected`

Typical meaning: shell tried to interpret the wrong file as text, or apktool invoked the wrong `aapt2`.

Check:

```bash
which aapt2
aapt2 version
apktool --version
```

For apktool 3.x, force the known-good Termux binary:

```bash
apktool b app_dir --aapt /data/data/com.termux/files/usr/bin/aapt2
```

If still broken, inspect exec chain:

```bash
strace -f -e execve -o /tmp/apktool.exec.log apktool b app_dir --aapt /data/data/com.termux/files/usr/bin/aapt2
rg aapt2 /tmp/apktool.exec.log
```

If the failing command omitted `--aapt`, fix that first before looking deeper.

## `invalid entry name '$...`

Typical meaning: decoded resources include filenames or references that start with `$`, and `aapt2` rejects them during rebuild.

Start narrow:

```bash
find app_dir/res -type f | rg '/\\$'
rg -n '@(drawable|mipmap)/\\$' app_dir/res
```

Then repair the exact names and references:

```bash
find app_dir/res -type f | rg '/\\$' | while read -r f; do
  dir="$(dirname "$f")"
  base="$(basename "$f")"
  mv "$f" "$dir/$(printf '%s' "$base" | sed 's/^\\$//')"
done
```

```bash
find app_dir/res -type f \\( -name '*.xml' -o -name '*.json' \\) | while read -r f; do
  sed -i 's#@drawable/\\$#@drawable/#g; s#@mipmap/\\$#@mipmap/#g' "$f"
done
```

Rebuild again with the Termux binary:

```bash
apktool b app_dir --aapt /data/data/com.termux/files/usr/bin/aapt2
```

## Resource compilation failure

Capture stderr:

```bash
apktool b app_dir --aapt /data/data/com.termux/files/usr/bin/aapt2 > build.stdout.log 2> build.stderr.log
tail -n 80 build.stderr.log
```

Then inspect only the named file:

```bash
rg -n "resource_name|style_name|attr_name" app_dir/res
sed -n '1,220p' app_dir/res/values/target.xml
```

Common causes:

- invalid XML after manual edit
- duplicate resource names
- unsupported attribute/value format
- file name not allowed by Android resource rules

## Signing or install failure

Check:

```bash
apksigner verify -v build/app-signed.apk
```

If install fails, inspect:

```bash
logcat | rg "INSTALL_FAILED|PackageManager|AndroidRuntime"
```

## Lost in big output

Do not re-run everything.

Use:

```bash
tail -n 80 build.stderr.log
rg -n "error:|Exception|INSTALL_FAILED" build.stderr.log
```
