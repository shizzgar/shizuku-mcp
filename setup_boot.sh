#!/bin/bash
BOOT_DIR="$HOME/.termux/boot"
mkdir -p "$BOOT_DIR"

cat <<EOF > "$BOOT_DIR/android-shizuku-mcp.sh"
#!/bin/bash
termux-wake-lock
cd "$PWD"
./run-server.sh > logs/boot.log 2>&1 &
EOF

chmod +x "$BOOT_DIR/android-shizuku-mcp.sh"
echo "Termux:Boot script created at $BOOT_DIR/android-shizuku-mcp.sh"
