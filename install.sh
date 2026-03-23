#!/bin/bash
set -e

echo "--- Настройка Android Shizuku MCP (Termux Optimized) ---"

# 1. Добавляем TUR (Termux User Repository) для готовых бинарников
echo "[1/5] Подключение репозитория TUR..."
pkg update -y
pkg install -y tur-repo

# 2. Устанавливаем системные пакеты (уже скомпилированные)
echo "[2/5] Установка системных бинарников (Pydantic, YAML и др.)..."
pkg install -y python python-pip termux-api openssl libffi binutils \
               python-pydantic python-pyyaml python-cryptography \
               python-httpx -y

# 3. Создаем venv с доступом к системным пакетам
echo "[3/5] Создание виртуального окружения..."
rm -rf venv
python -m venv venv --system-site-packages
source venv/bin/activate

# 4. Устанавливаем оставшиеся легкие зависимости через pip
echo "[4/5] Установка Python зависимостей через pip..."
pip install --upgrade pip
# Pip увидит системные pydantic/httpx/yaml и пропустит их
pip install mcp starlette uvicorn tenacity python-dotenv pydantic-settings

# 5. Проверка rish и создание конфигов
echo "[5/5] Финальная настройка..."
mkdir -p "$HOME/bin" artifacts logs
if [ -f "$HOME/bin/rish" ]; then
    chmod 700 "$HOME/bin/rish"
    echo "OK: rish найден в ~/bin/"
else
    echo "(!) Напоминание: не забудь скопировать rish в ~/bin/ после установки."
fi

if [ ! -f ".env" ]; then
    TOKEN=$(openssl rand -hex 16)
    echo "MCP_AUTH_TOKEN=$TOKEN" > .env
    echo "OK: Создан .env с токеном: $TOKEN"
fi

echo "------------------------------------------------"
echo "УСТАНОВКА ЗАВЕРШЕНА!"
echo "Запуск сервера: ./run-server.sh"
echo "------------------------------------------------"
