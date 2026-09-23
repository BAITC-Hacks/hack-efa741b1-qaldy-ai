# API application

Здесь будет FastAPI-приложение.

Планируемые внутренние каталоги:

```text
app/
├── api/
├── application/
├── domain/
├── infrastructure/
└── main.py
```

Первый vertical slice: `/health`, загрузка конфигурации и OpenAPI. Доменная логика не должна зависеть от FastAPI или конкретной базы данных.
