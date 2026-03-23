#!/bin/bash
# Переходим в директорию скрипта, если мы не в ней
cd "$(dirname "$0")"

if [ -d "venv" ]; then
    source venv/bin/activate
fi

export PYTHONUNBUFFERED=1
# Добавляем текущую директорию в PYTHONPATH, чтобы импорты из src.* работали
export PYTHONPATH=$PYTHONPATH:.

echo "--- Запуск Android Shizuku MCP сервера ---"
python src/main.py
