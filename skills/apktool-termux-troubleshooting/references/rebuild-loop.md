# Rebuild Loop

## Minimal loop

```bash
apktool b app_dir --aapt /data/data/com.termux/files/usr/bin/aapt2 -o build/app-unsigned.apk
apksigner sign --ks debug.keystore --out build/app-signed.apk build/app-unsigned.apk
apksigner verify -v build/app-signed.apk
pm install -r build/app-signed.apk
```

## Safer noisy loop

```bash
apktool b app_dir --aapt /data/data/com.termux/files/usr/bin/aapt2 -o build/app-unsigned.apk > build/stdout.log 2> build/stderr.log
tail -n 80 build/stderr.log
```

If the build succeeds:

```bash
apksigner sign --ks debug.keystore --out build/app-signed.apk build/app-unsigned.apk
apksigner verify -v build/app-signed.apk
pm install -r build/app-signed.apk
```

If launch still fails:

```bash
monkey -p com.example.target -c android.intent.category.LAUNCHER 1
logcat | rg "FATAL EXCEPTION|AndroidRuntime|VerifyError|ClassNotFoundException"
```
