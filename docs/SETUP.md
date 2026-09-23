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

По умолчанию `LLM_ENABLED=false`, поэтому внешний ключ для локального запуска не требуется. Для AI-режима задайте в локальном `.env` значения `LLM_ENABLED=true`, `LLM_API_KEY`, `LLM_BASE_URL` и `LLM_MODEL`. Не коммитьте `.env`: файл исключён через `.gitignore`.

## Датасет

Стартовый kit уже находится в репозитории:

```text
data/seed/career_quest_dataset/
├── skills.json
├── employees.json
├── events.json
└── activity_history.csv
```

Приложение читает эти файлы без изменений. Для другого расположения укажите абсолютный путь в переменной `DATASET_DIR`; Docker Compose уже монтирует каталог в API-контейнер.

## Запуск

```bash
docker compose up --build
```

Seed загружается при первом создании API service.

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

## Проверка пользовательского сценария

1. Откройте `http://localhost:3000`.
2. Выберите сотрудника из seed-датасета.
3. Проверьте целевой профиль, разрывы и 1–3 рекомендации.
4. Нажмите «Завершить активность» и проверьте блок `before → after` и обновлённый прогресс.

Рекомендации рассчитываются детерминированно без LLM. Завершения и импорты сохраняются в SQLite и восстанавливаются после перезапуска API. HR может загрузить JSON с `employees_json` и необязательным `activity_history_csv`, выполнить dry-run проверку, затем применить результат. В Compose `DATABASE_URL` по умолчанию указывает на `/data/runtime/career_quest.db` в постоянном Docker volume.

## Переменные окружения

`API_PORT` и `WEB_PORT` меняют публикуемые порты Compose. `NEXT_PUBLIC_API_URL` задаёт адрес API, встраиваемый при сборке web image, поэтому после его изменения пересоберите web. `DATASET_DIR` задаёт путь к seed; при запуске в Compose каталог также должен быть смонтирован. `DATABASE_URL` задаёт SQLite-файл с завершениями и импортами. `CORS_ORIGINS` — дополнительные origins API через запятую. `LLM_ENABLED`, `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` и `LLM_TIMEOUT_SECONDS` включают необязательный reranker.

На Windows PowerShell для локального запуска API активируйте окружение как `.\.venv\Scripts\Activate.ps1`.
