# Контракт API

Базовый адрес локально: `http://localhost:8000`. Полная интерактивная схема FastAPI доступна по `/docs`, OpenAPI JSON — по `/openapi.json`.

## Аутентификация

Защищённые маршруты принимают `Authorization: Bearer <token>`. Роль и ID сотрудника берутся из конфигурации API, а не из запроса:

- `DEMO_HR_TOKEN` задаёт токен HR;
- `DEMO_EMPLOYEE_TOKENS` задаёт JSON-объект вида `{"E0001":"<token>"}` для сотрудников. Каждый токен не короче 16 символов; токены должны быть уникальными.
- `GET /api/v1/auth/me` проверяет токен и возвращает роль и `employee_id`.

Employee-токен привязан к одному ID и не может читать другого сотрудника. HR-токен даёт доступ к списку сотрудников, HR-метрикам, импорту и разрешённому drill-down. Значения выдаются оператором демо; не помещайте реальные или рабочие credentials в Git. Web сохраняет введённый токен только в `sessionStorage` текущей вкладки.

В `APP_ENV=production`, `staging` и Vercel demo-auth отключён по умолчанию. Без проверенного OIDC/JWT adapter API откажет в защищённом доступе; `ALLOW_INSECURE_DEMO_AUTH=true` является только явным исключением для временного закрытого демо.

## Маршруты

| Метод | Путь | Доступ | Назначение |
|---|---|---|---|
| GET | `/livez` | без токена | Проверка процесса |
| GET | `/readyz` | без токена | Проверка готовности датасета и SQLite |
| GET | `/health` | без токена | Совместимый alias readiness-проверки |
| GET | `/api/v1/auth/me` | Bearer | Проверка demo-токена и получение роли/ID |
| GET | `/api/v1/employees?query=&limit=50` | HR | Поиск сотрудников, лимит 1–200 |
| GET | `/api/v1/employees/{employee_id}/journey` | Employee своего ID или HR | Полный профиль, baseline/effective skills, история, прогресс и рекомендации |
| POST | `/api/v1/employees/{employee_id}/recommendations` | Employee своего ID или HR | Пересчёт рекомендаций |
| POST | `/api/v1/employees/{employee_id}/activities/{event_id}/complete` | Employee своего ID или HR | Завершение; обязателен `Idempotency-Key` |
| GET | `/api/v1/hr/skill-gaps` | HR | Агрегаты дефицита навыков |
| GET | `/api/v1/hr/participation` | HR | Участие в активностях |
| GET | `/api/v1/hr/uncovered-employees` | HR | Сотрудники без подходящего шага |
| GET | `/api/v1/hr/catalog-gaps` | HR | Навыки без покрытия в каталоге |
| POST | `/api/v1/import/validate` | HR | Dry-run пакета профилей и необязательной истории |
| POST | `/api/v1/import/apply` | HR | Применение проверенного пакета |

HR-запросы поддерживают фильтры `department`, `role`, `grade` (`Junior`, `Middle`, `Senior`, `Lead`). Отсутствующий/неверный токен даёт 401, неверная роль или доступ к чужому employee ID — 403, отсутствующий сотрудник или событие — 404.

## Импорт

Validate принимает JSON вида `{"employees_json": <содержимое employees.json>, "activity_history_csv": "<CSV-текст>"}`; CSV можно опустить. Один пакет ограничен 10 000 сотрудников, 100 000 строк истории и 10 MB CSV-текста. Apply принимает `validation_token` и `package_hash` из результата validate, а также заголовок `Idempotency-Key` длиной до 128 символов. Токен проверки действует 15 минут; просроченные validation payload удаляются при следующих validate-операциях. Пакет применяется транзакционно; одинаковый повтор идемпотентен, конфликтующие строки отклоняются. Импорт увеличивает `dataset_revision`, поэтому процессы с общей БД пересобирают dataset bundle при следующем запросе.

Ответы `/api/*` содержат `Cache-Control: no-store`. Completion replay возвращает сохранённый исходный response snapshot (с `idempotent_replay=true`), а не пересчитывает его из более нового состояния.

## Примеры запросов

Примеры для Bash; заранее поместите выданные токены в `HR_TOKEN` и `EMPLOYEE_TOKEN`:

```bash
curl -H "Authorization: Bearer $HR_TOKEN" \
  'http://localhost:8000/api/v1/employees?limit=10'
curl -H "Authorization: Bearer $EMPLOYEE_TOKEN" \
  'http://localhost:8000/api/v1/employees/E0001/journey'
curl -X POST -H "Authorization: Bearer $EMPLOYEE_TOKEN" \
  -H 'Idempotency-Key: demo-001' \
  'http://localhost:8000/api/v1/employees/E0001/activities/EV_001/complete'
```

Подставляйте ID из активного набора данных. Для HR-проверки/применения передавайте заголовок `Authorization: Bearer $HR_TOKEN`:

```bash
curl -X POST http://localhost:8000/api/v1/import/validate \
  -H "Authorization: Bearer $HR_TOKEN" -H 'Content-Type: application/json' \
  --data-binary @evaluation-package.json
curl -X POST http://localhost:8000/api/v1/import/apply \
  -H "Authorization: Bearer $HR_TOKEN" -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: apply-evaluation-001' \
  --data '{"validation_token":"<token>","package_hash":"<hash>"}'
```

`evaluation-package.json` должен содержать объект `employees_json` со структурой `employees.json` и, при наличии истории, строковое поле `activity_history_csv`. Точные схемы запросов/ответов отображаются в `/docs`.
