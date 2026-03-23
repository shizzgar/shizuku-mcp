# 📊 СВОДНАЯ СТАТИСТИКА TERMUX-КОМАНД

## 🔢 Количество команд

| Категория | Количество |
|-----------|------------|
| **Всего файлов `termux-*`** | **83** |
| **Основные команды** | **72** |
| **SAF команды** | **9** |
| **API команды (требуют Termux:API)** | **~56** |
| **Базовые команды (без API)** | **12** |

---

## 📁 Распределение по категориям

### 🟢 Без Termux:API (12 команд)

| Команда | Описание |
|---------|----------|
| `termux-info` | Информация о Termux |
| `termux-change-repo` | Смена репозиториев |
| `termux-reset` | Сброс Termux |
| `termux-restore` | Восстановление |
| `termux-backup` | Бэкап |
| `termux-wake-lock` | Блокировка экрана |
| `termux-wake-unlock` | Разблокировка экрана |
| `termux-setup-storage` | Доступ к хранилищу |
| `termux-open` | Открыть файл |
| `termux-open-url` | Открыть URL |
| `termux-reload-settings` | Перезагрузка настроек |
| `termux-fix-shebang` | Исправление shebang |

### 🔵 Требуется Termux:API (~56 команд)

| Категория | Кол-во | Примеры |
|-----------|--------|----------|
| 🔋 Батарея/Дисплей | 4 | battery-status, brightness, torch, wallpaper |
| 📋 Буфер обмена | 2 | clipboard-get, clipboard-set |
| 🔔 Уведомления | 5 | toast, notification, notification-list, notification-remove, notification-channel |
| 🔊 Звук/Вибрация | 5 | volume, vibrate, audio-info, tts-engines, tts-speak |
| 📡 WiFi | 3 | scaninfo, connectioninfo, enable |
| 📍 Геолокация/Датчики | 2 | location, sensor |
| 📸 Камера/Медиа | 5 | camera-info, camera-photo, microphone-record, media-player, media-scan |
| 📱 Телеком | 8 | call-log, contact-list, sms-list, sms-send, telephony-call, ... |
| 🔐 Безопасность | 2 | fingerprint, keystore |
| 🔌 Спец. порты | 4 | nfc, usb, infrared-transmit, infrared-frequencies |
| ⏰ Планировщик | 1 | job-scheduler |
| 📱 Приложения | 4 | am, share, download, storage-get |

### 🟡 SAF Команды (9 команд)

| Команда | Описание |
|---------|----------|
| `termux-saf-dirs` | Список директорий |
| `termux-saf-ls` | Листинг файлов |
| `termux-saf-read` | Чтение файла |
| `termux-saf-write` | Запись в файл |
| `termux-saf-mkdir` | Создать директорию |
| `termux-saf-rm` | Удалить файл |
| `termux-saf-stat` | Info о файле |
| `termux-saf-create` | Создать файл |
| `termux-saf-managedir` | Управление дирекцией |

---

## 📈 Визуализация

```
ВСЕГО: 83 файла
├── Основные команды: 72 (86.7%)
├── SAF команды: 9 (10.8%)
└── Вспомогательные: 2 (2.5%)

ПО ТИПУ:
├── Без API: 12 (14.5%)
├── С API: 56 (67.5%)
└── SAF: 9 (10.8%)
```

---

## 💡 Быстрый старт

```bash
# 1. Проверка установленных команд
ls -1 /data/data/com.termux/files/usr/bin/termux-* | wc -l

# 2. Список всех команд
compgen -c | grep ^termux- | sort

# 3. Поиск команды по названию
compgen -c | grep -i "wifi" | grep termux

# 4. Проверка API
pkg installed | grep termux-api
```

---

*Сгенерировано: 23 марта 2026, 20:36*

# 📱 Полный справочник команд Termux

## Автоматически сгенерированный документ

Этот документ содержит описание всех доступных команд `termux-*` в Termux.

---

## 📋 Список всех команд


---

## 📖 Категории команд

### 🔧 **Базовые команды Termux** (не требуют API)

| Команда | Описание | Пример |
|---------|----------|--------|
| `termux-info` | Информация о Termux и устройстве | `termux-info` |
| `termux-change-repo` | Смена репозиториев | `termux-change-repo` |
| `termux-reset` | Сброс Termux | `termux-reset` |
| `termux-restore` | Восстановление из бэкапа | `termux-restore` |
| `termux-backup` | Создание бэкапа | `termux-backup` |
| `termux-wake-lock` | Блокировка отключения экрана | `termux-wake-lock &` |
| `termux-wake-unlock` | Разблокировка экрана | `killall termux-wake-lock` |
| `termux-setup-storage` | Доступ к /sdcard | `termux-setup-storage` |
| `termux-open` | Открыть файл в приложении | `termux-open file.pdf` |
| `termux-open-url` | Открыть URL в браузере | `termux-open-url https://...` |
| `termux-reload-settings` | Перезагрузка настроек | `termux-reload-settings` |
| `termux-fix-shebang` | Исправление shebang | `termux-fix-shebang script.sh` |
| `termux-fingerprint` | Проверка отпечатка | `termux-fingerprint` |

### 🔋 **Энергоснабжение и Дисплей**

| Команда | Описание | Пример |
|---------|----------|--------|
| `termux-battery-status` | Статус батареи (JSON) | `termux-battery-status \| jq .` |
| `termux-brightness` | Управление яркостью | `termux-brightness 50` |
| `termux-torch` | Фонарик | `termux-torch toggle` |
| `termux-wallpaper` | Обои | `termux-wallpaper set image.jpg` |

### 📋 **Буфер обмена**

| Команда | Описание | Пример |
|---------|----------|--------|
| `termux-clipboard-get` | Получить из буфера | `termux-clipboard-get` |
| `termux-clipboard-set` | Записать в буфер | `termux-clipboard-set "text"` |

### 🔔 **Уведомления и UI**

| Команда | Описание | Пример |
|---------|----------|--------|
| `termux-toast` | Всплывающее уведомление | `termux-toast "Hello"` |
| `termux-notification` | Системное уведомление | `termux-notification -t "T" -m "M"` |
| `termux-notification-list` | Список уведомлений | `termux-notification-list` |
| `termux-notification-remove` | Удалить уведомление | `termux-notification-remove id` |
| `termux-notification-channel` | Канал уведомлений | `termux-notification-channel list` |
| `termux-dialog` | Диалоговые окна | `termux-dialog msgbox "Hello"` |

### 🔊 **Звук и Вибрация**

| Команда | Описание | Пример |
|---------|----------|--------|
| `termux-volume` | Громкость | `termux-volume 50` |
| `termux-vibrate` | Вибрация | `termux-vibrate 1000` |
| `termux-audio-info` | Аудио инфо | `termux-audio-info` |
| `termux-tts-engines` | TTS движки | `termux-tts-engines` |
| `termux-tts-speak` | Текст в речь | `termux-tts-speak "Hello"` |

### 📡 **Сеть и WiFi**

| Команда | Описание | Пример |
|---------|----------|--------|
| `termux-wifi-scaninfo` | Сканирование WiFi | `termux-wifi-scaninfo \| jq .` |
| `termux-wifi-connectioninfo` | WiFi подключение | `termux-wifi-connectioninfo` |
| `termux-wifi-enable` | Вкл/выкл WiFi | `termux-wifi-enable` |

### 📍 **Геолокация и Датчики**

| Команда | Описание | Пример |
|---------|----------|--------|
| `termux-location` | Геолокация | `termux-location \| jq .` |
| `termux-sensor` | Датчики | `termux-sensor gyroscope 1` |

### 📸 **Камера и Медиа**

| Команда | Описание | Пример |
|---------|----------|--------|
| `termux-camera-info` | Info камеры | `termux-camera-info` |
| `termux-camera-photo` | Сделать фото | `termux-camera-photo /sdcard/photo.jpg` |
| `termux-microphone-record` | Запись аудио | `termux-microphone-record /sdcard/record.mp3` |
| `termux-media-player` | Медиа плеер | `termux-media-player /sdcard/file.mp3` |
| `termux-media-scan` | Сканировать медиа | `termux-media-scan /sdcard/file.mp3` |

### 📱 **Телекоммуникации**

| Команда | Описание | Пример |
|---------|----------|--------|
| `termux-call-log` | Журнал звонков | `termux-call-log` |
| `termux-contact-list` | Контакты | `termux-contact-list` |
| `termux-sms-inbox` | Входящие SMS | `termux-sms-inbox` |
| `termux-sms-list` | Список SMS | `termux-sms-list` |
| `termux-sms-send` | Отправить SMS | `termux-sms-send --number +7... --text "Hi"` |
| `termux-telephony-call` | Позвонить | `termux-telephony-call tel:+7...` |
| `termux-telephony-deviceinfo` | Info устройства | `termux-telephony-deviceinfo` |
| `termux-telephony-cellinfo` | Info ячейки | `termux-telephony-cellinfo` |

### 📂 **SAF - Storage Access Framework**

| Команда | Описание | Пример |
|---------|----------|--------|
| `termux-saf-dirs` | Список директорий | `termux-saf-dirs` |
| `termux-saf-ls` | Листинг файлов | `termux-saf-ls` |
| `termux-saf-read` | Чтение файла | `termux-saf-read file.txt` |
| `termux-saf-write` | Запись в файл | `termux-saf-write file.txt "content"` |
| `termux-saf-mkdir` | Создать директорию | `termux-saf-mkdir newdir` |
| `termux-saf-rm` | Удалить файл | `termux-saf-rm file.txt` |
| `termux-saf-stat` | Info о файле | `termux-saf-stat file.txt` |
| `termux-saf-create` | Создать файл | `termux-saf-create newfile.txt` |
| `termux-saf-managedir` | Управление дирекцией | `termux-saf-managedir` |

### 📱 **Приложения и Система**

| Команда | Описание | Пример |
|---------|----------|--------|
| `termux-am` | Android Activity Manager | `termux-am start com.package` |
| `termux-share` | Поделиться | `termux-share --type text/plain --data "text"` |
| `termux-download` | Загрузить файл | `termux-download https://example.com/file` |
| `termux-storage-get` | Получить путь к хранилищу | `termux-storage-get` |

### 🔐 **Безопасность**

| Команда | Описание | Пример |
|---------|----------|--------|
| `termux-fingerprint` | Отпечаток пальца | `termux-fingerprint` |
| `termux-keystore` | Хранилище ключей | `termux-keystore --put key value` |

### 🔌 **Специальные порты**

| Команда | Описание | Пример |
|---------|----------|--------|
| `termux-nfc` | NFC чтение/запись | `termux-nfc read` |
| `termux-usb` | USB OTG | `termux-usb --list` |
| `termux-infrared-transmit` | ИК-передатчик | `termux-infrared-transmit --frequency 38000` |
| `termux-infrared-frequencies` | Частоты ИК | `termux-infrared-frequencies` |

### ⏰ **Планировщик**

| Команда | Описание | Пример |
|---------|----------|--------|
| `termux-job-scheduler` | Планировщик задач | `termux-job-scheduler --command "cmd"` |

### 🛠️ **Системные утилиты**

| Команда | Описание | Пример |
|---------|----------|--------|
| `termux-setup-package-manager` | Настройка пакетов | `termux-setup-package-manager` |
| `termux-exec-ld-preload-lib` | LD_PRELOAD | - |
| `termux-exec-system-linker-exec` | Системный линкер | - |
| `termux-am-socket` | AM сокет | - |
| `termux-api-start` | Запуск API | - |
| `termux-api-stop` | Остановка API | - |

### 📦 **Переменные окружения**

| Команда | Описание | Пример |
|---------|----------|--------|
| `termux-apps-info-app-version-name` | Версия приложения | `termux-apps-info-app-version-name --package com.termux` |
| `termux-apps-info-env-variable` | Env переменные | `termux-apps-info-env-variable --package com.termux` |
| `termux-scoped-env-variable` | Scoped env var | `termux-scoped-env-variable --put VAR value` |

---

## 🎯 Практические примеры

### 1. Мониторинг батареи

```bash
#!/bin/bash
while true; do
    status=$(termux-battery-status | jq -r '.percent')
    termux-toast "Батарея: $status%"
    sleep 60
done
```

### 2. Автоматическое уведомление

```bash
#!/bin/bash
termux-notification \
    -t "Напоминание" \
    -m "Время выпить воды!" \
    -s "water_reminder"
termux-vibrate 1000
```

### 3. WiFi сканер

```bash
#!/bin/bash
termux-wifi-scaninfo | jq '.results[] | {ssid: .ssid, level: .level}' | sort
```

### 4. Геолокация логу

```bash
#!/bin/bash
while true; do
    loc=$(termux-location | jq -c '.')
    echo "Mon Mar 23 20:33:33 MSK 2026: $loc" >> ~/location.log
    sleep 300
done
```

### 5. Голосовой ввод

```bash
#!/bin/bash
text=$(termux-speech-to-text)
termux-clipboard-set "$text"
termux-toast "Скопировано: $text"
```

### 6. Яркость по времени

```bash
#!/bin/bash
hour=$(date +%H)
if [ $hour -ge 22 ] || [ $hour -le 6 ]; then
    termux-brightness 50
else
    termux-brightness 200
fi
```

### 7. Фонарик через терминал

```bash
#!/bin/bash
case "$1" in
    on)    termux-torch on ;;
    off)   termux-torch off ;;
    toggle) termux-torch toggle ;;
    *)     echo "Usage: flashlight {on|off|toggle}" ;;
esac
```

### 8. Бэкап данных

```bash
#!/bin/bash
dir=$(termux-storage-get)
if [ -n "$dir" ]; then
    mkdir -p ~/backup
    rsync -avz $dir/Documents/ ~/backup/documents/
    termux-toast "Бэкап завершен!"
fi
```

### 9. Уведомление о звонке

```bash
#!/bin/bash
while true; do
    new_call=$(termux-call-log | tail -1)
    if [ -n "$new_call" ]; then
        termux-notification -t "Новый звонок" -m "$new_call"
    fi
    sleep 60
done
```

### 10. SMS монитор

```bash
#!/bin/bash
last_count=$(termux-sms-list | wc -l)
while true; do
    current_count=$(termux-sms-list | wc -l)
    if [ $current_count -gt $last_count ]; then
        new_sms=$(termux-sms-list | tail -n +$((last_count + 1)))
        termux-toast "Новое SMS!"
        termux-vibrate 500
    fi
    last_count=$current_count
    sleep 30
done
```

---

## 📚 Дополнительные ресурсы

- **Официальная документация:** https://wiki.termux.com/
- **Termux:API GitHub:** https://github.com/termux/termux-api
- **Форум:** https://github.com/termux/termux-app/discussions

---

## ⚠️ Важные заметки

1. **Termux:API** требуется для большинства команд `termux-*` с доступом к Android API
2. Некоторые команды требуют **разрешений** (геолокация, SMS, контакты)
3. Для работы в фоне используйте `nohup` или `tmux`
4. Команды SAF позволяют работать с файлами **без root**

---

*Документ сгенерирован автоматически в Termux*  
*Дата: Mon Mar 23 20:33:33 MSK 2026*
