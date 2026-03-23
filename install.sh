#!/bin/bash
set -e

echo "--- Настройка Android Shizuku MCP для Termux ---"

# 1. Обновляем пакеты и ставим системные зависимости (уже собранные)
echo "[1/5] Установка системных пакетов (бинарников)..."
pkg update -y
pkg install -y python python-pip termux-api openssl libffi binutils \
               python-pydantic python-cryptography python-httpx \
               python-pydantic-settings python-yaml -y

# 2. Создаем venv с доступом к системным пакетам
echo "[2/5] Создание виртуального окружения (с поддержкой системных пакетов)..."
rm -rf venv
python -m venv venv --system-site-packages
source venv/bin/activate

# 3. Обновляем pip и ставим только то, чего нет в pkg
echo "[3/5] Установка оставшихся Python зависимостей..."
pip install --upgrade pip
# Ставим mcp и остальное. Pip увидит pydantic в системе и не будет его собирать.
pip install mcp starlette uvicorn tenacity python-dotenv pydantic-settings pyyaml

# 4. Проверка rish
echo "[4/5] Проверка Shizuku rish..."
mkdir -p "$HOME/bin"
if [ ! -f "$HOME/bin/rish" ]; then
    echo "(!) ВНИМАНИЕ: rish не найден в ~/bin/rish."
    echo "    Пожалуйста, экспортируй rish из приложения Shizuku в ~/bin/"
else
    chmod 700 "$HOME/bin/rish"
    echo "OK: rish найден и настроен."
fi

# 5. Генерация конфига
echo "[5/5] Настройка конфигурации..."
mkdir -p artifacts logs
if [ ! -f ".env" ]; then
    TOKEN=$(openssl rand -hex 16)
    echo "MCP_AUTH_TOKEN=$TOKEN" > .env
    echo "OK: Создан .env с новым токеном: $TOKEN"
else
    echo "OK: .env уже существует."
fi

echo "------------------------------------------------"
echo "УСТАНОВКА ЗАВЕРШЕНА!"
echo "Запуск сервера: ./run-server.sh"
echo "------------------------------------------------"
