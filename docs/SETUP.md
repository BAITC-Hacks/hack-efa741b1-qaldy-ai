# Настройка и запуск

## Требования

Основной путь:

- Git;
- Docker Desktop или Docker Engine;
- Docker Compose v2.

Для запуска без Docker дополнительно потребуются Python и Node.js. Точные версии будут зафиксированы в Dockerfiles и manifest-файлах на этапе bootstrap.

## Получение проекта

```bash
git clone https://github.com/BAITC-Hacks/hack-efa741b1-qaldy-ai.git
cd hack-efa741b1-qaldy-ai
```

## Настройка окружения

Linux/macOS:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

По умолчанию `LLM_ENABLED=false`, поэтому внешний ключ для локального запуска не требуется. Для AI-режима будут использоваться `LLM_API_KEY`, `LLM_BASE_URL` и `LLM_MODEL`.

## Размещение датасета

Создай каталог `data/seed/career_quest_dataset` и помести туда файлы стартового kit:

```text
data/seed/career_quest_dataset/
├── skills.json
├── employees.json
├── events.json
└── activity_history.csv
```

Исходные данные исключены из Git в первом этапе и не должны изменяться приложением.

## Целевой запуск

После bootstrap-этапа:

```bash
docker compose up --build
```

Seed и миграции должны выполняться автоматически и идемпотентно.

Проверка:

```bash
curl http://localhost:8000/health
```

Ожидаемые адреса:

- `http://localhost:3000` — web;
- `http://localhost:8000` — API;
- `http://localhost:8000/docs` — OpenAPI.

Остановка:

```bash
docker compose down
```

## Текущее состояние первого коммита

Этот коммит содержит план, структуру и контракт запуска. Исполняемые сервисы и Docker-конфигурация намеренно добавляются следующим отдельным коммитом. Это сохраняет понятную историю разработки и не выдаёт неподтверждённые команды за работающую реализацию.
