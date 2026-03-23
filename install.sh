#!/bin/bash
set -e

echo "--- Настройка Android Shizuku MCP (Сборка из исходников) ---"
echo "(!) ВНИМАНИЕ: Сейчас начнется сборка Rust-пакетов (Pydantic)."
echo "    Это может занять 5-15 минут. Не закрывайте Termux."

# 1. Установка полного стека для компиляции
echo "[1/4] Установка инструментов сборки (Rust, Clang, Build-Essential)..."
pkg update -y
pkg install -y python python-pip termux-api openssl libffi binutils \
               rust clang build-essential make -y

# 2. Подготовка виртуального окружения
echo "[2/4] Создание чистого виртуального окружения..."
rm -rf venv
python -m venv venv
source venv/bin/activate

# 3. Установка зависимостей с компиляцией
echo "[3/4] Сборка и установка Python-пакетов (это займет время)..."
pip install --upgrade pip setuptools wheel

# Прокидываем пути для линковщика, чтобы он видел системные либы Termux
export LDFLAGS="-L${PREFIX}/lib"
export CPPFLAGS="-I${PREFIX}/include"

# Устанавливаем всё скопом. Pip сам скачает исходники и вызовет rustc/clang.
pip install mcp starlette uvicorn tenacity python-dotenv pydantic-settings pyyaml httpx

# 4. Финальные штрихи
echo "[4/4] Завершение настройки..."
mkdir -p "$HOME/bin" artifacts logs
if [ -f "$HOME/bin/rish" ]; then
    chmod 700 "$HOME/bin/rish"
fi

if [ ! -f ".env" ]; then
    TOKEN=$(openssl rand -hex 16)
    echo "MCP_AUTH_TOKEN=$TOKEN" > .env
fi

echo "------------------------------------------------"
echo "ГОТОВО! Всё собрано и установлено."
echo "Если нужно сэкономить место (200МБ+), можешь удалить rust:"
echo "pkg uninstall rust clang build-essential -y"
echo "------------------------------------------------"
echo "Запуск сервера: ./run-server.sh"
echo "------------------------------------------------"
