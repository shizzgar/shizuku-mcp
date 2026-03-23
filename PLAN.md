Я отвечу как архитектор Android automation и MCP-интеграций.

**TL;DR**: ниже готовое ТЗ для coding-агента на реализацию **open-source MCP-сервера в Termux**, который даёт LLM управлять Android через **Shizuku/rish** и, где уместно, через **Termux:API**. В ТЗ уже заложены важные ограничения: **Streamable HTTP** по актуальной спецификации MCP, требования безопасности для локального HTTP-транспорта, перезапуск Shizuku после ребута на non-root, а также особенность Android 14+ для `rish`. ([modelcontextprotocol.io][1])

Ниже текст, который можно отдавать агенту почти без правок.

---

# Техническое задание

## 1. Название проекта

**android-shizuku-mcp**

## 2. Цель

Разработать полностью open-source MCP-сервер, запускаемый **на самом Android-устройстве в Termux**, который предоставляет LLM-агенту безопасный и ограниченный набор инструментов для управления устройством.

Сервер должен:

* работать в **Termux**;
* использовать **MCP Streamable HTTP transport**;
* для привилегированных действий вызывать **Shizuku `rish`**;
* для непривилегированных действий использовать **Termux:API**;
* быть пригодным для реального локального использования на Android 11+ без ПК после первоначальной настройки wireless debugging;
* уметь стартовать автоматически через **Termux:Boot**. MCP Streamable HTTP в актуальной спецификации реализуется как независимый серверный процесс с одним endpoint, поддерживающим `POST` и `GET`; Python SDK MCP поддерживает `stdio`, `SSE` и `Streamable HTTP`. ([modelcontextprotocol.io][1])

## 3. Целевая платформа и ограничения

### Обязательная поддержка

* Android 11+
* non-root устройство
* Termux
* Shizuku
* Python-реализация сервера

### Желательная поддержка

* rooted device через Sui/Shizuku backend
* Android 14+

### Ограничения платформы

На non-root устройствах Shizuku нужно запускать заново после каждого ребута; на Android 11+ это можно делать через wireless debugging прямо на устройстве. `rish` — это оболочка для выполнения команд в высокопривилегированном shell-процессе; по сути он передаёт аргументы удалённому shell, например `rish -c 'ls'` выполняется как `/system/bin/sh -c 'ls'`. Для Android 14+ релизы Shizuku отдельно отмечают, что `rish` не должен лежать в writeable-месте вроде `/sdcard`; файл нужно копировать во внутренний каталог терминального приложения и убирать write permission. ([shizuku.rikka.app][2])

## 4. Что именно нужно сделать

Нужно реализовать локальный MCP-сервер, который даёт агенту типизированные инструменты для:

* открытия приложений и deep links;
* запуска Android intents;
* получения списка пакетов;
* остановки приложений;
* снятия скриншота;
* записи экрана;
* чтения базовой системной информации;
* работы с буфером обмена, уведомлениями и другими возможностями через Termux:API;
* выполнения **ограниченного** набора shell-команд через `rish`.

Сервер **не должен** по умолчанию давать агенту “сырой полный shell без ограничений”. Raw shell допускается только как отдельный выключенный по умолчанию режим для продвинутого пользователя.

## 5. Архитектура

### 5.1 Общая схема

LLM Agent
→ MCP client
→ `android-shizuku-mcp` в Termux
→ Router layer
→ либо `rish -c ...` для привилегированных Android shell-действий
→ либо `termux-*` / `termux-api` для обычных Android API
→ возврат structured JSON результата агенту

### 5.2 Обязательные внутренние модули

1. **MCP transport layer**

   * Streamable HTTP
   * один endpoint, например `/mcp`
   * поддержка MCP session handling

2. **Tool registry**

   * регистрация всех tools
   * JSON-schema для аргументов
   * описания tools, пригодные для LLM

3. **Command router**

   * маршрутизация в `rish`, `termux-api` или локальные Python-функции

4. **Privilege boundary**

   * явное разделение на:

     * safe tools
     * privileged tools
     * dangerous tools

5. **Execution layer**

   * subprocess wrapper
   * timeout
   * stdout/stderr capture
   * exit-code mapping

6. **State and artifacts**

   * каталог для временных артефактов
   * screenshots
   * logs
   * optional recorded videos

7. **Health/doctor module**

   * проверка наличия:

     * Termux
     * Python deps
     * Termux:API
     * `rish`
     * статуса Shizuku
     * writable/non-writable `rish`
     * доступности endpoint

## 6. Технический стек

### Обязательный стек

* Python 3.11+
* официальный **MCP Python SDK**
* Termux
* Termux:API
* Shizuku + `rish`

MCP Python SDK официально поддерживает создание MCP-серверов и транспорты `stdio`, `SSE` и `Streamable HTTP`. Termux:API — это add-on, который предоставляет Android API в CLI и скрипты. ([GitHub][3])

### Рекомендуемые библиотеки

* `mcp`
* `pydantic`
* `httpx`
* `uvicorn` или встроенный транспорт из MCP SDK
* `orjson` при необходимости
* `tenacity` для retry
* `python-dotenv`

## 7. Требования к MCP-слою

### 7.1 Transport

Реализовать **Streamable HTTP** transport.

Требования:

* единый endpoint `/mcp`
* поддержка `POST` и `GET`
* корректная работа MCP lifecycle: initialize → operation → shutdown
* поддержка `Mcp-Session-Id`, если transport/SDK её использует

В актуальной спецификации Streamable HTTP сервер обязан иметь один endpoint для `POST` и `GET`, а клиент после получения `Mcp-Session-Id` должен передавать его в последующих запросах. ([modelcontextprotocol.io][1])

### 7.2 Безопасность транспорта

Обязательные требования:

* bind только на `127.0.0.1`
* проверка `Origin`
* bearer token или другой простой локальный auth-механизм
* request timeout
* rate limiting на опасные tools
* отключаемая, но по умолчанию включённая auth-защита

Спецификация MCP отдельно требует в Streamable HTTP валидировать `Origin`, рекомендует локальный bind на `127.0.0.1` и аутентификацию, чтобы не допустить DNS rebinding и несанкционированный доступ к локальному серверу. ([modelcontextprotocol.io][1])

## 8. Набор MCP tools

Ниже — минимально обязательный набор.

### 8.1 Диагностика

#### `doctor()`

Возвращает:

* версия Android
* наличие Termux:API
* наличие `rish`
* путь до `rish`
* признак доступности Shizuku
* текущий backend: adb/root/unknown
* есть ли проблема Android 14+ с permissions у `rish`
* доступность каталога артефактов
* версия сервера

#### `ping()`

Простой healthcheck.

### 8.2 Приложения и intents

#### `list_packages(third_party_only: bool = true, filter: str | null = null)`

Возвращает список пакетов.

#### `open_app(package_name: str)`

Открывает приложение.

#### `force_stop(package_name: str)`

Останавливает приложение.

#### `start_intent(action: str | null, data: str | null, package: str | null, component: str | null, extras: object | null)`

Запускает intent.

#### `open_url(url: str)`

Открывает URL через intent.

### 8.3 Экран и артефакты

#### `take_screenshot()`

Делает скриншот, сохраняет локально, возвращает:

* абсолютный путь
* размер файла
* timestamp

#### `record_screen(duration_sec: int = 10)`

Пишет видео экрана, возвращает путь к файлу.

#### `list_artifacts()`

Список артефактов.

#### `read_artifact_metadata(path: str)`

Возвращает метаданные артефакта.

### 8.4 Утилиты через Termux:API

#### `clipboard_get()`

#### `clipboard_set(text: str)`

#### `show_notification(title: str, content: str)`

#### `battery_status()`

#### `wifi_status()`

#### `device_info()`

Эти действия предпочтительно реализовывать через Termux:API, а не через `rish`, когда для них не нужны повышенные привилегии. Termux:API специально предназначен для вызова Android API из CLI и скриптов. ([GitHub][4])

### 8.5 Привилегированные shell-tools

#### `shell_readonly(command: str)`

Разрешить только whitelist-команды, например:

* `pm list packages`
* `getprop`
* `settings get`
* `dumpsys` для безопасных разделов
* `cmd package resolve-activity`
* `am start ...`
* `screencap`
* `screenrecord`

#### `shell_privileged(command: str, confirm_dangerous: bool = false)`

Опциональный tool.
По умолчанию выключен.
Включается через config flag.
Должен:

* требовать `confirm_dangerous=true`
* логировать все вызовы
* иметь timeout
* блокировать явно опасные шаблоны

### 8.6 Конфигурация и статус

#### `get_server_config()`

Возвращает безопасную часть конфига.

#### `reload_config()`

Перечитывает конфиг.

## 9. Политика безопасности для shell

### 9.1 По умолчанию запрещено

* `rm -rf /`
* любые команды с `su`/`sudo`
* изменение сетевых правил
* destructive `pm uninstall`, если явно не включено
* `settings put global` и аналогичные действия без allowlist
* `reboot`, `svc power shutdown`
* запись в произвольные системные каталоги
* shell pipelines с подстановкой, если включён safe mode

### 9.2 Разрешённая модель

Инструменты должны быть **типизированными**, а не строиться вокруг одного generic shell tool.

### 9.3 Исполнение shell

Все команды должны запускаться без shell-инъекции, насколько это возможно:

* использовать список аргументов вместо строк там, где реально возможно;
* если вызывается `rish -c`, формировать команду из шаблонов и проверенного набора аргументов;
* пользовательский input экранировать;
* вести audit log.

## 10. Работа с `rish`

### Обязательные требования

* при старте выполнять autodetect `rish`
* проверять права на файл `rish`
* на Android 14+ автоматически предупреждать, если `rish` лежит в неподходящем месте или имеет write permission
* хранить `rish` в приватном каталоге Termux, не на `/sdcard`

### Переменные окружения

Учесть поведение `RISH_PRESERVE_ENV`. В README `rish` отмечено, что если backend работает через adb, Termux-переменные окружения могут мешать доступу к внутренним путям; при adb backend unset-значение трактуется как `0`. Сервер должен:

* либо явно задавать `RISH_PRESERVE_ENV=0`,
* либо жёстко использовать абсолютные пути к исполняемым файлам и минимальное окружение. ([GitHub][5])

### Проверка доступности

Нужен внутренний вызов наподобие:

* `rish -c 'id'`
* `rish -c 'getprop ro.build.version.release'`

Если команда не проходит, сервер должен вернуть нормализованную ошибку вида:

* `SHIZUKU_NOT_RUNNING`
* `RISH_NOT_FOUND`
* `RISH_PERMISSION_INVALID`
* `COMMAND_TIMEOUT`

## 11. Конфигурация

Нужен файл `config.toml` или `config.yaml`.

Минимальные параметры:

* `host = "127.0.0.1"`
* `port = 8765`
* `endpoint = "/mcp"`
* `auth_token = "..."`
* `artifacts_dir = "..."`
* `logs_dir = "..."`
* `enable_raw_shell = false`
* `max_command_timeout_sec = 20`
* `allow_package_force_stop = true`
* `allow_screenrecord = true`
* `allowed_shell_patterns = [...]`
* `denied_shell_patterns = [...]`

## 12. Логирование

Нужно реализовать:

* access log
* tool call log
* privileged action log
* error log

Логи не должны содержать:

* auth token
* полный clipboard content, если это может быть чувствительно
* секреты из env

Для каждого tool call логировать:

* timestamp
* tool name
* sanitized args
* duration
* result status
* exit code при subprocess

## 13. Установка и bootstrap

Нужно подготовить автоматизированный bootstrap:

### 13.1 Скрипт установки

`install.sh` должен:

* обновить пакеты Termux
* установить Python и зависимости
* установить Python deps
* проверить наличие Termux:API
* проверить наличие `rish`
* создать каталоги конфигурации, логов и артефактов
* сгенерировать пример конфига
* вывести инструкцию по запуску

### 13.2 Скрипт запуска

`run-server.sh` должен:

* экспортировать минимальное окружение
* запускать сервер
* печатать локальный URL

### 13.3 Автозапуск

Подготовить boot-скрипт для `~/.termux/boot/`, который:

* берёт wake lock при необходимости
* запускает сервер в фоне
* пишет логи в файл

Termux:Boot запускает скрипты из `~/.termux/boot/` в отсортированном порядке; README рекомендует при необходимости вызывать `termux-wake-lock` первым действием. ([GitHub][6])

## 14. Поведение после ребута

Так как на non-root устройстве Shizuku требует повторного запуска после каждой перезагрузки, сервер должен:

* стартовать через Termux:Boot даже если Shizuku ещё не поднят;
* в `doctor()` и в privileged-tools возвращать понятную ошибку, что сервер жив, но Shizuku не активен;
* не падать полностью из-за отсутствующего backend;
* продолжать обслуживать safe tools и Termux:API tools.

Это критично, потому что на non-root startup-steps Shizuku действительно нужно повторять после каждого reboot. ([GitHub][7])

## 15. Ошибки и формат ответов

Все tools должны возвращать структурированный JSON.

Пример успешного ответа:

```json
{
  "ok": true,
  "data": {
    "package_name": "org.mozilla.firefox",
    "launched": true
  }
}
```

Пример ошибки:

```json
{
  "ok": false,
  "error": {
    "code": "SHIZUKU_NOT_RUNNING",
    "message": "Shizuku backend is not available",
    "details": {
      "tool": "open_app"
    }
  }
}
```

Стандартизировать коды:

* `INVALID_ARGUMENT`
* `UNAUTHORIZED`
* `TOOL_DISABLED`
* `RISH_NOT_FOUND`
* `RISH_PERMISSION_INVALID`
* `SHIZUKU_NOT_RUNNING`
* `TERMUX_API_NOT_AVAILABLE`
* `COMMAND_TIMEOUT`
* `COMMAND_FAILED`
* `ARTIFACT_NOT_FOUND`

## 16. Структура проекта

Рекомендуемая структура:

```text
android-shizuku-mcp/
  pyproject.toml
  README.md
  LICENSE
  .env.example
  config.example.toml
  install.sh
  run-server.sh
  scripts/
    bootstrap_rish.sh
    setup_boot.sh
  src/
    main.py
    config.py
    logging_setup.py
    errors.py
    models.py
    security.py
    doctor.py
    artifacts.py
    runners/
      subprocess_runner.py
      rish_runner.py
      termux_api_runner.py
    tools/
      doctor_tools.py
      app_tools.py
      intent_tools.py
      shell_tools.py
      screen_tools.py
      utility_tools.py
    mcp/
      server.py
      auth.py
      session.py
  tests/
    test_config.py
    test_security.py
    test_tool_schemas.py
    test_rish_runner.py
    test_termux_api_runner.py
```

## 17. README

README должен содержать:

* что делает проект
* архитектуру
* зависимости
* инструкцию для Termux
* установку Shizuku
* пример запуска
* пример конфигурации
* пример подключения MCP-клиента
* раздел troubleshooting
* объяснение ограничений non-root режима

## 18. Критерии приёмки

Проект считается принятым, если выполнено всё ниже.

### 18.1 Функционально

* сервер запускается в Termux;
* endpoint Streamable HTTP доступен локально;
* `ping()` работает;
* `doctor()` корректно показывает состояние;
* `list_packages()`, `open_app()`, `open_url()`, `take_screenshot()`, `clipboard_get()/set()` работают;
* при выключенном raw shell опасные команды недоступны;
* при неактивном Shizuku сервер не падает и возвращает нормальную ошибку;
* скриншоты сохраняются и доступны как артефакты.

### 18.2 По безопасности

* bind только на localhost;
* есть проверка `Origin`;
* есть auth token;
* dangerous tools логируются;
* нет unrestricted raw shell по умолчанию.

### 18.3 По качеству реализации

* есть type hints;
* есть unit tests;
* есть README;
* есть пример конфигурации;
* есть install script;
* есть boot script.

## 19. Тестовый сценарий приёмки

Агент должен прогнать такой сценарий:

1. Установить зависимости.
2. Запустить сервер.
3. Вызвать `ping()`.
4. Вызвать `doctor()`.
5. Вызвать `list_packages()`.
6. Вызвать `open_url("https://example.org")`.
7. Вызвать `take_screenshot()`.
8. Вызвать `clipboard_set("hello")`, затем `clipboard_get()`.
9. Выключить Shizuku и убедиться, что `open_app()` возвращает `SHIZUKU_NOT_RUNNING`, а `clipboard_get()` продолжает работать.
10. Перезапустить Shizuku и убедиться, что privileged tools снова работают.

## 20. Что не нужно делать в первой версии

Не нужно в v1:

* OCR
* computer vision анализ скриншотов
* accessibility automation
* gesture injection
* полноценный UI agent
* remote internet exposure сервера
* WebSocket transport
* сложную OAuth-схему

## 21. Итоговые артефакты от coding-агента

Нужно сдать:

* исходный код проекта;
* `README.md`;
* `LICENSE`;
* `config.example.toml`;
* `install.sh`;
* `run-server.sh`;
* `setup_boot.sh`;
* unit tests;
* краткий `ARCHITECTURE.md`;
* `SECURITY.md` с описанием рисков и ограничений.

## 22. Приоритет реализации

### Must-have

* Streamable HTTP MCP server
* auth + localhost bind + Origin check
* `doctor`
* `list_packages`
* `open_app`
* `open_url`
* `take_screenshot`
* `clipboard_get/set`
* `show_notification`
* artifacts
* boot script
* README

### Should-have

* `record_screen`
* `force_stop`
* whitelist shell tool
* auto-detect проблем `rish`

### Could-have

* raw shell behind flag
* structured package search
* richer diagnostics
* import/export config profiles

---

Если хочешь, я сразу превращу это в ещё более удобную версию: **“ТЗ + пошаговый implementation plan для coding-agent”** или **“ТЗ в формате `AGENTS.md`/`CLAUDE.md`”**.

[1]: https://modelcontextprotocol.io/specification/2025-03-26/basic/transports "Transports - Model Context Protocol"
[2]: https://shizuku.rikka.app/guide/setup/ "User manual | Shizuku"
[3]: https://github.com/modelcontextprotocol/python-sdk "GitHub - modelcontextprotocol/python-sdk: The official Python SDK for Model Context Protocol servers and clients · GitHub"
[4]: https://github.com/termux/termux-api "GitHub - termux/termux-api: Termux add-on app which exposes device functionality as API to command line programs. · GitHub"
[5]: https://github.com/RikkaApps/Shizuku-API/blob/master/rish/README.md "Shizuku-API/rish/README.md at master · RikkaApps/Shizuku-API · GitHub"
[6]: https://github.com/termux/termux-boot "GitHub - termux/termux-boot: Termux add-on app allowing programs to be run at boot. · GitHub"
[7]: https://github.com/RikkaApps/Shizuku-API "GitHub - RikkaApps/Shizuku-API: The API and the developer guide for Shizuku and Sui. · GitHub"
