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

По умолчанию API читает `data/seed/career_quest_dataset` из корня репозитория. Другой путь можно передать через `DATASET_DIR`. Завершения хранятся в in-memory overlay, поэтому после перезапуска процесса исходный seed снова становится единственным источником состояния.

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
