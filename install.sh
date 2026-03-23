#!/bin/bash
set -e

echo "--- Настройка Android Shizuku MCP (Samsung S22 Ultra Fix) ---"

# 1. Установка инструментов сборки
echo "[1/4] Установка инструментов сборки..."
pkg update -y
pkg install -y python python-pip termux-api openssl libffi binutils \
               rust clang build-essential make -y

# 2. Определение Android API Level (Критично для Maturin/Pydantic)
SDK_LEVEL=$(getprop ro.build.version.sdk)
export ANDROID_API_LEVEL=${SDK_LEVEL:-33}
export CARGO_BUILD_TARGET="aarch64-linux-android"

echo "Detected Android API Level: $ANDROID_API_LEVEL"

# 3. Подготовка виртуального окружения
echo "[2/4] Создание виртуального окружения..."
rm -rf venv
python -m venv venv
source venv/bin/activate

# 4. Сборка и установка
echo "[3/4] Сборка Pydantic (теперь с указанием API Level)..."
pip install --upgrade pip setuptools wheel

# Прокидываем флаги компиляции
export LDFLAGS="-L${PREFIX}/lib"
export CPPFLAGS="-I${PREFIX}/include"

# Сама установка
pip install mcp starlette uvicorn tenacity python-dotenv pydantic-settings pyyaml httpx

# 5. Завершение
echo "[4/4] Финальная настройка..."
mkdir -p "$HOME/bin" artifacts logs
[ -f "$HOME/bin/rish" ] && chmod 700 "$HOME/bin/rish"

if [ ! -f ".env" ]; then
    echo "MCP_AUTH_TOKEN=$(openssl rand -hex 16)" > .env
fi

echo "------------------------------------------------"
echo "ПОБЕДА! Всё собрано."
echo "Запуск: ./run-server.sh"
echo "------------------------------------------------"
