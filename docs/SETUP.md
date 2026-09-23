# Настройка и запуск

## Требования

Основной путь:

- Git;
- Docker Desktop или Docker Engine;
- Docker Compose v2.

Для запуска без Docker дополнительно потребуются Python 3.12+ и Node.js 22+.

## Получение проекта

```bash
git clone https://github.com/BAITC-Hacks/hack-efa741b1-qaldy-ai.git
cd hack-efa741b1-qaldy-ai
```

## Настройка окружения

Linux/macOS:

```bash
sed '/^DEMO_HR_TOKEN=/d' .env.example > .env
printf 'DEMO_HR_TOKEN=%s\n' "$(openssl rand -hex 32)" >> .env
```

Windows PowerShell:

```powershell
.\scripts\setup-demo-auth.ps1
```

Скрипт создаёт случайный HR-токен в `.env` и показывает его один раз для входа в web-интерфейс. Если токен уже задан, он сохраняется без изменений. Для отдельного сотруднического входа добавьте в `.env` JSON-словарь `DEMO_EMPLOYEE_TOKENS`, где ключ — ID сотрудника, значение — его уникальный токен длиной от 16 символов. Роль и ID определяет только API по токену; клиент не может назначить их себе заголовками. HR-токен позволяет просматривать профили и импортировать данные.

По умолчанию `LLM_ENABLED=false`, поэтому внешний ключ для локального запуска не требуется. Для AI-reranking задайте в локальном `.env` значения `LLM_ENABLED=true`, `LLM_API_KEY`, `LLM_BASE_URL` и `LLM_MODEL`. Не коммитьте `.env`: файл исключён через `.gitignore`.

Demo-аутентификация использует `AUTH_MODE=demo` и `Authorization: Bearer <token>`. Для проверки токена доступен `GET /api/v1/auth/me`. В production/staging и Vercel она fail-closed по умолчанию; переменная `ALLOW_INSECURE_DEMO_AUTH=true` ослабляет это поведение только для временного закрытого демо и не заменяет production identity provider.

## Датасет

Стартовый kit уже находится в репозитории:

```text
data/seed/career_quest_dataset/
├── skills.json
├── employees.json
├── events.json
└── activity_history.csv
```

Приложение читает эти файлы без изменений. Для другого расположения укажите абсолютный путь в переменной `DATASET_DIR`; Docker Compose уже монтирует каталог в API-контейнер.

## Запуск

```bash
docker compose up --build
```

На чистом checkout Compose автоматически использует локальные demo-токены `local-demo-employee-token-2026` для `E0001` и `local-demo-hr-token-2026` для HR. Эти значения предназначены только для синтетического локального демо; `.env` переопределяет их.

Seed загружается при первом создании API service.

Проверка:

```bash
curl http://localhost:8000/health
```

Ожидаемые адреса:

- `http://localhost:3000` — web;
- `http://localhost:8000` — API;
- `http://localhost:8000/docs` — OpenAPI.

Остановка:

```bash
docker compose down
```

## Запуск без Docker

API:

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Web в отдельном терминале:

```bash
cd apps/web
npm ci
npm run dev
```

На Windows активируйте Python-окружение командой `.\.venv\Scripts\Activate.ps1`.

## Проверка пользовательского сценария

1. Откройте `http://localhost:3000` и через меню профиля введите employee-токен. Для чистого Compose это `local-demo-employee-token-2026`, привязанный к `E0001`; при наличии `.env` используйте выданный токен из `DEMO_EMPLOYEE_TOKENS`.
2. Откройте `/journey`: сотруднику доступен его собственный профиль.
3. Проверьте целевой профиль, разрывы и 1–3 рекомендации.
4. Нажмите «Завершить активность» у доступной добровольной рекомендации и проверьте блок `before → after` и обновлённый прогресс.
5. Через меню профиля замените employee-токен на HR-токен, откройте HR-обзор и проверьте агрегаты. HR может выбирать произвольный профиль и импортировать данные, но не отмечать активность выполненной от имени сотрудника.

Рекомендации рассчитываются детерминированно без LLM. Завершения и импорты сохраняются в SQLite и восстанавливаются после перезапуска API. HR может загрузить JSON с `employees_json` и необязательным `activity_history_csv`, выполнить dry-run проверку, затем применить результат. В Compose `DATABASE_URL` по умолчанию указывает на `/data/runtime/career_quest.db` в постоянном Docker volume.

## Переменные окружения

`API_PORT` и `WEB_PORT` меняют публикуемые порты Compose. `NEXT_PUBLIC_API_URL` задаёт адрес API, встраиваемый при сборке web image, поэтому после его изменения пересоберите web. `DATASET_DIR` задаёт путь к seed; при запуске в Compose каталог также должен быть смонтирован. `DATABASE_URL` задаёт SQLite-файл с завершениями и импортами. `CORS_ORIGINS` — дополнительные origins API через запятую. `AUTH_MODE` выбирает auth adapter (сейчас поддержан только `demo`); `DEMO_HR_TOKEN` задаёт HR-токен, а `DEMO_EMPLOYEE_TOKENS` — JSON-словарь персональных токенов; `ALLOW_INSECURE_DEMO_AUTH` — явное временное исключение для закрытого публичного демо. `LLM_ENABLED`, `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` и `LLM_TIMEOUT_SECONDS` включают необязательный reranker.

На Windows PowerShell для локального запуска API активируйте окружение как `.\.venv\Scripts\Activate.ps1`.
