#!/bin/bash
set -e

echo "--- Настройка Android Shizuku MCP (Умная установка) ---"

# 1. Инструменты сборки (проверяем, нужно ли доставлять)
echo "[1/4] Проверка инструментов сборки..."
pkg update -y
pkg install -y python python-pip termux-api openssl libffi binutils \
               rust clang build-essential make git -y

# 2. Подготовка виртуального окружения
if [ -d "venv" ]; then
    echo "[2/4] Виртуальное окружение уже существует. Пропускаем создание."
else
    echo "[2/4] Создание нового виртуального окружения..."
    python -m venv venv
fi

source venv/bin/activate

# 3. Установка зависимостей (с защитой от пересборки)
echo "[3/4] Проверка и установка Python-пакетов..."
pip install --upgrade pip setuptools wheel

# Проверяем, установлен ли pydantic-core (самый тяжелый)
if python -c "import pydantic_core" 2>/dev/null; then
    echo "OK: Тяжелые зависимости (Pydantic) уже собраны. Пропускаем компиляцию."
    # Доставляем только если что-то изменилось в коде сервера
    pip install -e . --no-deps 2>/dev/null || true
    # На случай если нужно обновить легкие пакеты
    pip install starlette uvicorn tenacity python-dotenv pydantic-settings pyyaml httpx mcp
else
    echo "(!) Тяжелые зависимости не найдены. Начинаем сборку (это один раз)..."
    SDK_LEVEL=$(getprop ro.build.version.sdk)
    export ANDROID_API_LEVEL=${SDK_LEVEL:-33}
    export CARGO_BUILD_TARGET="aarch64-linux-android"
    export LDFLAGS="-L${PREFIX}/lib"
    export CPPFLAGS="-I${PREFIX}/include"
    
    pip install mcp starlette uvicorn tenacity python-dotenv pydantic-settings pyyaml httpx
fi

# 4. Финальная настройка
echo "[4/4] Завершение..."
mkdir -p "$HOME/bin" artifacts logs
[ -f "$HOME/bin/rish" ] && chmod 700 "$HOME/bin/rish"

if [ ! -f ".env" ]; then
    TOKEN=$(python -c "import secrets; print(secrets.token_hex(16))")
    echo "MCP_AUTH_TOKEN=$TOKEN" > .env
    echo "OK: Создан .env с токеном: $TOKEN"
fi

echo "------------------------------------------------"
echo "ГОТОВО! Всё настроено."
echo "Запуск: ./run-server.sh"
echo "------------------------------------------------"
