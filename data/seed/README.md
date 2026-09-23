# Seed data

Стартовый kit локально размещается в `data/seed/career_quest_dataset/`:

- `skills.json`
- `employees.json`
- `events.json`
- `activity_history.csv`

Файлы датасета входят в репозиторий и не изменяются приложением. Loader проверяет согласованность метаданных и уникальность записей. Завершения активностей и применённые импорты хранятся отдельно в SQLite по `DATABASE_URL`; Docker Compose подключает для БД постоянный volume. Детали формата и HTTP-импорта описаны в [`career_quest_dataset/README.ru.md`](career_quest_dataset/README.ru.md) и [`../../docs/API.md`](../../docs/API.md).
