# API application

FastAPI-приложение с модульными слоями:

```text
app/
├── api/              HTTP routes
├── application/      use cases
├── domain/           модели и будущие правила рекомендаций
├── infrastructure/   будущие loaders, repositories и LLM adapter
└── main.py
```

Текущий vertical slice:

- `GET /health`;
- `GET /api/v1/demo/employee-journey`.

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
