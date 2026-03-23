#!/bin/bash
set -e

echo "--- Настройка Android Shizuku MCP (Termux Mirror Fix) ---"

# 1. Исправление репозитория TUR
echo "[1/5] Настройка рабочего зеркала TUR..."
pkg update -y
pkg install -y tur-repo || true

# Используем альтернативное зеркало, если основное лежит
if [ -f "$PREFIX/etc/apt/sources.list.d/tur.list" ]; then
    echo "deb https://tur-repo.pages.dev/tur-packages tur tur" > "$PREFIX/etc/apt/sources.list.d/tur.list"
    pkg update -y
fi

# 2. Попытка поставить готовые пакеты
echo "[2/5] Попытка установки бинарников из репозитория..."
INSTALL_RUST=false
if pkg install -y python python-pip termux-api openssl libffi binutils \
               python-pydantic python-pyyaml python-cryptography \
               python-httpx -y; then
    echo "OK: Использованы готовые бинарники."
else
    echo "(!) Бинарники не найдены. Придется собрать Pydantic вручную."
    echo "    Это займет время, Rust будет удален после сборки."
    pkg install -y rust clang -y
    INSTALL_RUST=true
fi

# 3. Виртуальное окружение
echo "[3/5] Подготовка venv..."
rm -rf venv
python -m venv venv --system-site-packages
source venv/bin/activate

# 4. Установка через Pip
echo "[4/5] Установка Python-пакетов..."
pip install --upgrade pip
pip install mcp starlette uvicorn tenacity python-dotenv pydantic-settings

# 5. Чистка Rust (если ставили)
if [ "$INSTALL_RUST" = true ]; then
    echo "Очистка: Удаление Rust и Clang..."
    # Оставляем clang если он нужен был для чего-то еще, но rust точно трем
    pkg uninstall -y rust -y
    pkg clean
fi

# 6. Конфиги
echo "[6/5] Завершение..."
mkdir -p "$HOME/bin" artifacts logs
if [ -f "$HOME/bin/rish" ]; then
    chmod 700 "$HOME/bin/rish"
fi

if [ ! -f ".env" ]; then
    echo "MCP_AUTH_TOKEN=$(openssl rand -hex 16)" > .env
fi

echo "------------------------------------------------"
echo "УСПЕШНО! Можешь запускать ./run-server.sh"
echo "------------------------------------------------"
