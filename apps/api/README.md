# API application

FastAPI-приложение с разделением на HTTP-маршруты (`api`), use cases (`application`), доменные модели и расчёты (`domain`), а также loader, SQLite repository и LLM adapter (`infrastructure`).

## Основные маршруты

- `GET /livez`, `GET /readyz`, `GET /health` — liveness/readiness.
- `GET /api/v1/auth/me` — проверка Bearer demo-токена.
- Employee journey, recommendations и completion — `/api/v1/employees/*`.
- HR-аналитика — `/api/v1/hr/skill-gaps`, `/participation`, `/uncovered-employees`, `/catalog-gaps`.
- Импорт — `POST /api/v1/import/validate` и `POST /api/v1/import/apply`.

Полный контракт и примеры: [`../../docs/API.md`](../../docs/API.md).

## Локальный запуск

Требуются Python 3.12+. API требует задать `DEMO_HR_TOKEN` и/или `DEMO_EMPLOYEE_TOKENS` (JSON-словарь `employee_id → token`); каждый token должен иметь не менее 16 символов. Получите demo-токены для локального запуска, не используйте реальные credentials. Пример ниже задаёт только формат:

```powershell
$env:DEMO_HR_TOKEN = '<выданный HR token>'
$env:DEMO_EMPLOYEE_TOKENS = '{"E0001":"<выданный employee token>"}'
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

macOS/Linux: вместо `$env:...` используйте `export DEMO_HR_TOKEN=...` и `export DEMO_EMPLOYEE_TOKENS='{"E0001":"..."}'`. Не записывайте рабочие токены в Git.

API читает seed из `data/seed/career_quest_dataset`; путь можно переопределить через `DATASET_DIR`. Завершения и импорт сохраняются в SQLite по `DATABASE_URL`. Для Docker Compose постоянная БД расположена на volume `career_quest_runtime`.

## Тесты

Из каталога `apps/api` после установки зависимостей:

```bash
python -m pytest
```
