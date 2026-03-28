#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

AAPT2_PATH="/data/data/com.termux/files/usr/bin/aapt2"

usage() {
  echo "usage: apktool-build-termux.sh <project_dir> <output_apk> [--debuggable]" >&2
  exit 2
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
fi

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
  usage
fi

PROJECT_DIR="$1"
OUTPUT_APK="$2"
DEBUGGABLE_FLAG="${3:-}"

if [ ! -d "$PROJECT_DIR" ]; then
  echo "project_dir does not exist: $PROJECT_DIR" >&2
  exit 1
fi

if [ ! -x "$AAPT2_PATH" ]; then
  echo "missing Termux aapt2: $AAPT2_PATH" >&2
  exit 1
fi

if [ -n "$DEBUGGABLE_FLAG" ] && [ "$DEBUGGABLE_FLAG" != "--debuggable" ]; then
  usage
fi

mkdir -p "$(dirname "$OUTPUT_APK")"

CMD=(
  apktool
  b
  "$PROJECT_DIR"
  --aapt
  "$AAPT2_PATH"
  -o
  "$OUTPUT_APK"
)

if [ "$DEBUGGABLE_FLAG" = "--debuggable" ]; then
  CMD+=(--debuggable)
fi

exec "${CMD[@]}"
