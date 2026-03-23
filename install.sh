#!/bin/bash
set -e

echo "--- Настройка Android Shizuku MCP (Samsung S22 Ultra Fix) ---"

# 1. Инструменты сборки
echo "[1/4] Установка инструментов сборки..."
pkg update -y
pkg install -y python python-pip termux-api openssl libffi binutils \
               rust clang build-essential make -y

# 2. SDK Level для Maturin
SDK_LEVEL=$(getprop ro.build.version.sdk)
export ANDROID_API_LEVEL=${SDK_LEVEL:-33}
export CARGO_BUILD_TARGET="aarch64-linux-android"

# 3. Виртуальное окружение
echo "[2/4] Создание виртуального окружения..."
rm -rf venv
python -m venv venv
source venv/bin/activate

# 4. Сборка и установка
echo "[3/4] Установка Python-пакетов..."
pip install --upgrade pip setuptools wheel
export LDFLAGS="-L${PREFIX}/lib"
export CPPFLAGS="-I${PREFIX}/include"
pip install mcp starlette uvicorn tenacity python-dotenv pydantic-settings pyyaml httpx

# 5. Финальная настройка
echo "[4/4] Завершение..."
mkdir -p "$HOME/bin" artifacts logs
[ -f "$HOME/bin/rish" ] && chmod 700 "$HOME/bin/rish"

if [ ! -f ".env" ]; then
    # Используем Python для генерации токена (надежнее чем openssl)
    TOKEN=$(python -c "import secrets; print(secrets.token_hex(16))")
    echo "MCP_AUTH_TOKEN=$TOKEN" > .env
    echo "OK: Создан .env с токеном: $TOKEN"
fi

echo "------------------------------------------------"
echo "ПОБЕДА! Всё собрано."
echo "Запуск: ./run-server.sh"
echo "------------------------------------------------"
