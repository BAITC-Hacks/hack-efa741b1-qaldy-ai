# API application

FastAPI-приложение с модульными слоями:

```text
app/
├── api/              HTTP routes
├── application/      use cases
├── domain/           модели данных и результата рекомендаций
├── infrastructure/   loader seed-датасета
└── main.py
```

Текущий core flow:

- `GET /health`;
- `GET /api/v1/employees`;
- `GET /api/v1/employees/{employee_id}/journey`;
- `POST /api/v1/employees/{employee_id}/recommendations`;
- `POST /api/v1/employees/{employee_id}/activities/{event_id}/complete` с заголовком `Idempotency-Key`.
- HR analytics: `/api/v1/hr/skill-gaps`, `/participation`, `/uncovered-employees`, `/catalog-gaps`.
- HR import: `POST /api/v1/import/validate` и `POST /api/v1/import/apply`.

По умолчанию API читает `data/seed/career_quest_dataset` из корня репозитория. Другой путь можно передать через `DATASET_DIR`. Завершения и импортированные профили/история сохраняются в SQLite. Путь задаётся через `DATABASE_URL` (Compose по умолчанию использует `/data/runtime/career_quest.db`). Employee endpoints используют демонстрационные заголовки; список сотрудников, HR routes и импорт доступны только с `X-Demo-Role: hr`. Подробности — в [`../../docs/API.md`](../../docs/API.md).

Локальный запуск:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Тесты:

```bash
pytest
```
