# Настройка и запуск

## Требования

Основной путь:

- Git;
- Docker Desktop или Docker Engine;
- Docker Compose v2.

Для запуска без Docker дополнительно потребуются Python 3.12+ и Node.js 22+.

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

## Запуск

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

## Запуск без Docker

API:

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Web в отдельном терминале:

```bash
cd apps/web
npm ci
npm run dev
```

На Windows активируйте Python-окружение командой `.\.venv\Scripts\Activate.ps1`.

## Текущее состояние

Первый рабочий vertical slice использует demo-профиль, возвращаемый API. Полный dataset importer, persistence и расчёт рекомендаций по реальным файлам добавляются следующими этапами.
