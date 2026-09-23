# Контракт API

Базовый адрес локально: `http://localhost:8000`. Полная интерактивная схема генерируется FastAPI по адресу `/docs`; OpenAPI JSON доступен по `/openapi.json`.

## Доступ

Demo API использует заголовок `X-Demo-Role: employee` или `X-Demo-Role: hr`. Для employee-запросов к ресурсу конкретного сотрудника передавайте `X-Employee-Id: <employee_id>`; сотрудник может читать и обновлять только собственный профиль. HR может запрашивать employee journey и HR-аналитику. Роль `hr` для списка сотрудников и HR routes обязательна. Это заголовки для демонстрации, они не подтверждают реальную личность.

## Маршруты

| Метод | Путь | Доступ | Назначение |
|---|---|---|---|
| GET | `/health` | без заголовков | Проверка доступности процесса |
| GET | `/api/v1/employees?query=&limit=50` | HR | Поиск сотрудников, лимит 1–200 |
| GET | `/api/v1/employees/{employee_id}/journey` | Employee (свой ID) или HR | Профиль, прогресс, навыки и рекомендации |
| POST | `/api/v1/employees/{employee_id}/recommendations` | Employee (свой ID) или HR | Пересчёт выдачи рекомендаций |
| POST | `/api/v1/employees/{employee_id}/activities/{event_id}/complete` | Employee (свой ID) или HR | Завершить событие; обязателен `Idempotency-Key` |
| GET | `/api/v1/hr/skill-gaps` | HR | Агрегаты дефицита навыков |
| GET | `/api/v1/hr/participation` | HR | Участие в активностях |
| GET | `/api/v1/hr/uncovered-employees` | HR | Сотрудники без подходящего шага |
| GET | `/api/v1/hr/catalog-gaps` | HR | Пробелы каталога активностей |
| POST | `/api/v1/import/validate` | HR | Проверить пакет профилей и необязательную историю без применения |
| POST | `/api/v1/import/apply` | HR | Атомарно применить пакет после успешной проверки |

Для HR-маршрутов поддерживаются query-фильтры `department`, `role`, `grade` (`Junior`, `Middle`, `Senior`, `Lead`). Ошибка доступа возвращает 401/403, неизвестный сотрудник или событие — 404. Demo-заголовки не подтверждают личность и предназначены только для демонстрации.

Импорт принимает JSON вида `{"employees_json": <содержимое employees.json>, "activity_history_csv": "<CSV-текст>"}`; поле CSV можно опустить. Apply принимает `validation_token` и `package_hash`, полученные при проверке, и требует заголовок `Idempotency-Key`. Токен проверки действует 15 минут. После успешного apply новые профили и история сразу включаются в текущий набор данных, а при запуске API восстанавливаются из SQLite. Повторное применение идентичного пакета идемпотентно; конфликтующие строки отклоняются.

## Примеры

```bash
curl -H 'X-Demo-Role: hr' 'http://localhost:8000/api/v1/employees?limit=10'
curl -H 'X-Demo-Role: employee' -H 'X-Employee-Id: EMP-001' \
  'http://localhost:8000/api/v1/employees/EMP-001/journey'
curl -X POST -H 'X-Demo-Role: employee' -H 'X-Employee-Id: EMP-001' \
  -H 'Idempotency-Key: demo-001' \
  'http://localhost:8000/api/v1/employees/EMP-001/activities/EVT-001/complete'
```

Подставьте ID, существующие в seed-наборе. Список текущих сотрудников можно получить HR-запросом. Точные поля запросов и ответов смотрите в `/docs`.

## Примеры импорта

```bash
curl -X POST http://localhost:8000/api/v1/import/validate \
  -H 'Content-Type: application/json' -H 'X-Demo-Role: hr' \
  --data-binary @evaluation-package.json
curl -X POST http://localhost:8000/api/v1/import/apply \
  -H 'Content-Type: application/json' -H 'X-Demo-Role: hr' \
  -H 'Idempotency-Key: apply-evaluation-001' \
  --data '{"validation_token":"<token>","package_hash":"<hash>"}'
```

Файл `evaluation-package.json` должен содержать объект `employees_json` со структурой `employees.json` и, при наличии истории, строковое поле `activity_history_csv`.
