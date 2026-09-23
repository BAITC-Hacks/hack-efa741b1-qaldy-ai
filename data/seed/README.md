# Seed data

Стартовый kit локально размещается в `data/seed/career_quest_dataset/`:

- `skills.json`
- `employees.json`
- `events.json`
- `activity_history.csv`

Файлы датасета входят в репозиторий и не изменяются приложением. Loader проверяет согласованность метаданных и уникальность записей, а пользовательские завершения сохраняются отдельно в in-memory overlay.
