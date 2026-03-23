#!/bin/bash
set -e

echo "=================================================="
echo "   ULTIMATE ANDROID MCP SETUP (Android 12-15)    "
echo "=================================================="

# Пути к rish
RISH_PATHS=("$HOME/bin/rish" "/data/data/com.termux/files/usr/bin/rish" "$(which rish 2>/dev/null)")
FOUND_RISH=""

for p in "${RISH_PATHS[@]}"; do
    if [ -n "$p" ] && [ -f "$p" ]; then
        FOUND_RISH="$p"
        break
    fi
done

# 1. Системные хаки (через Shizuku/rish)
echo "[1/6] Пытаемся отключить Phantom Process Killer..."
if [ -n "$FOUND_RISH" ]; then
    echo "Используем rish: $FOUND_RISH"
    $FOUND_RISH -c "/system/bin/device_config put activity_manager max_phantom_processes 2147483647" || true
    $FOUND_RISH -c "/system/bin/settings put global settings_enable_monitor_phantom_procs false" || true
    echo "OK: Системные лимиты расширены."
else
    echo "(!) rish не найден. Пропускаем тюнинг (экспортируй rish из Shizuku)."
fi

# 2. Установка пакетов
echo "[2/6] Установка системных пакетов..."
pkg update -y
pkg install -y python python-pip termux-api openssl libffi binutils \
               rust clang build-essential make git -y

# 3. Настройка разрешений
echo "[3/6] СЕЙЧАС ОТКРОЮТСЯ НАСТРОЙКИ ПРИЛОЖЕНИЙ."
echo "ДЛЯ КАЖДОГО (Termux и Termux:API) СДЕЛАЙ:"
echo "1. Батарея -> Не ограничено (Unrestricted)"
echo "2. Разрешения -> Дать все"
echo "3. Отображение поверх других приложений -> Разрешить"
sleep 2

# Открываем настройки Termux
am start -a android.settings.APPLICATION_DETAILS_SETTINGS -d package:com.termux || true
read -p "Нажми ENTER когда закончишь с Termux..."

# Открываем настройки Termux:API
am start -a android.settings.APPLICATION_DETAILS_SETTINGS -d package:com.termux.api || true
read -p "Нажми ENTER когда закончишь с Termux:API..."

# 4. Запуск основного инсталлера
echo "[4/6] Запуск установки зависимостей..."
chmod +x install.sh
./install.sh

# 5. Настройка автозапуска
echo "[5/6] Настройка автозапуска (Termux:Boot)..."
chmod +x setup_boot.sh
./setup_boot.sh

# 6. Финальная проверка
echo "[6/6] Проверка готовности..."
echo "--- ТЕСТ ТЕРМИНАЛА ---"
if termux-battery-status > /dev/null 2>&1; then
    echo "✅ Termux:API РАБОТАЕТ"
else
    echo "❌ Termux:API ВСЁ ЕЩЁ ВИСИТ (проверь разрешения)"
fi

echo "=================================================="
echo "УСТАНОВКА ЗАВЕРШЕНА!"
echo "Запусти сервер: ./run-server.sh"
echo "=================================================="
