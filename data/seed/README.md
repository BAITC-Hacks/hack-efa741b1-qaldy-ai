# Seed data

Стартовый kit локально размещается в `data/seed/career_quest_dataset/`:

- `skills.json`
- `employees.json`
- `events.json`
- `activity_history.csv`

Файлы датасета не коммитятся на первом этапе и не изменяются приложением. Seed importer должен читать их идемпотентно и сохранять пользовательские изменения отдельно.
