# QALDY AI — Career Quest

Приложение для построения карьерной траектории сотрудника: показывает разрывы навыков, предлагает объяснимые следующие шаги и пересчитывает прогресс после завершения активности.

## JTBD

### Сотрудник

**Когда** я готовлюсь к следующему грейду или новой роли, **я хочу** видеть разрывы между моими навыками и требованиями цели и получать достижимые активности с понятным объяснением, **чтобы** выбрать следующий шаг развития и отслеживать свой прогресс.

### HR и команда развития

**Когда** я планирую развитие сотрудников, **я хочу** видеть общие дефициты навыков, участие в активностях и случаи, где нет подходящей рекомендации, **чтобы** определять приоритеты обучения и улучшать каталог развития.

## Быстрый запуск

Требуются Docker Desktop (или Docker Engine) и Docker Compose v2.

На Windows можно запустить web и API без Docker:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\start-local.ps1
```

Скрипт запускает оба сервиса в фоне, создаёт demo HR-токен при необходимости и открывает приложение по адресу `http://localhost:3000`. Токен выводится в консоль. Логи находятся в `%TEMP%\qaldy-career-quest-local`.

```powershell
docker compose up --build
```

Для чистого checkout Compose использует только локальные demo-токены: `local-demo-employee-token-2026` для сотрудника `E0001` и `local-demo-hr-token-2026` для HR. Их можно заменить секретными значениями в `.env` через `.\scripts\setup-demo-auth.ps1`. Откройте [главную страницу](http://localhost:3000), введите нужный токен через меню профиля, затем используйте траекторию, HR-обзор, импорт или [схему API](http://localhost:8000/docs). Без настройки LLM рекомендации рассчитываются детерминированно.

Последовательность показа обязательного сценария и импорта профиля жюри приведена в [JURY_DEMO.md](JURY_DEMO.md).

Стартовый набор содержит 200 синтетических профилей, 40 активностей, 60 навыков и 2 743 записи истории. Схемы описаны в [README датасета](data/seed/career_quest_dataset/README.ru.md).

Чтобы остановить сервисы, выполните `docker compose down`. Именованный Docker volume `career_quest_runtime` хранит runtime-БД с завершениями активностей и импортированными профилями/историей.

## Проверки и CI

GitHub Actions запускает проверки при каждом `push` и `pull_request`:

- API: установка Python-зависимостей разработки и `pytest`.
- Web: `npm ci`, ESLint, проверка TypeScript, unit-тесты Vitest и Playwright E2E на production-сборке Next.js.

Для запуска проверок локально используйте Python 3.12+ и Node.js 22.x.

Backend (из корня репозитория):

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
```

Frontend (из корня репозитория):

```powershell
cd apps/web
npm ci
npm run lint
npm run typecheck
npm test
npm run build
npx playwright install chromium
npm run test:e2e
```

Playwright E2E запускает production-сервер Next.js и использует web fixtures; это проверка интерфейса, не сквозная проверка с запущенным FastAPI. В CI Chromium устанавливается автоматически.

Для AI-reranking задайте `LLM_ENABLED=true` и `LLM_API_KEY` в локальном `.env`; без них сохраняется детерминированный режим. Секреты не добавляйте в Git.

## Структура

```text
apps/api/       FastAPI API, доменная логика и тесты
apps/web/       Next.js интерфейс сотрудника и HR
data/seed/      начальный набор JSON/CSV
docs/           настройка, архитектура, API и формат данных
```

## Документация

- [Настройка и запуск](docs/SETUP.md)
- [Архитектура](docs/ARCHITECTURE.md)
- [Контракт API и demo-доступ](docs/API.md)
- [Формат seed-датасета](docs/DATASET.md)
- [Движок рекомендаций](docs/RECOMMENDATION_ENGINE.md)
- [План разработки и известные пробелы](docs/PROJECT_PLAN.md)
- [Backend API](apps/api/README.md)
- [Web-приложение](apps/web/README.md)

## Статус и ограничения

- Основной путь сотрудника и HR-аналитика реализован на seed-данных.
- Employee- и HR-доступ определяются серверными demo Bearer-токенами. Это не production identity provider; публичное окружение по умолчанию закрывает demo-auth.
- HR может загрузить `employees.json` и необязательный `activity_history.csv`, проверить их через dry-run и применить. Импортированные записи доступны в профилях, рекомендациях и HR-агрегатах; они сохраняются в SQLite.
- Завершения активности и результаты импорта хранятся в SQLite по `DATABASE_URL` и переживают перезапуск API.
- Веб-страницы дополнительных разделов продукта могут использовать локальные демонстрационные данные; наличие страницы не означает наличие live API.

Перед использованием для реальных сотрудников замените demo-авторизацию, перенесите SQLite на production-grade хранилище с резервным копированием и согласуйте обработку персональных данных.
