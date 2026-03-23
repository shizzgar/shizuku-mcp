#!/bin/bash
# Переходим в директорию скрипта
cd "$(dirname "$0")"

# Гарантируем, что пути Termux приоритетны
export PREFIX="/data/data/com.termux/files/usr"
export PATH="$PREFIX/bin:$PATH"
export LD_LIBRARY_PATH="$PREFIX/lib"

if [ -d "venv" ]; then
    source venv/bin/activate
fi

export PYTHONUNBUFFERED=1
export PYTHONPATH=$PYTHONPATH:.

echo "--- Запуск Android Shizuku MCP сервера ---"
# Проверяем наличие termux-api перед запуском для логов
if command -v termux-battery-status >/dev/null 2>&1; then
    echo "✅ Termux:API бинарники видны в PATH"
else
    echo "❌ ВНИМАНИЕ: Termux:API бинарники НЕ видны в PATH"
fi

python src/main.py
