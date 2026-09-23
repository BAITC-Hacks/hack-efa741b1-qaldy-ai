# QALDY AI — Career Quest

Career Quest — AI-навигатор развития сотрудника для трека Halyk Bank на HackAlem AI. Система сопоставляет профиль сотрудника, историю участия и требования целевого грейда, затем предлагает 1–3 объяснимых шага развития и показывает изменение прогресса после выполнения активности.

## Основной сценарий

1. Сотрудник открывает профиль и видит текущие навыки и карьерную цель.
2. Система рассчитывает разрывы до целевого профиля.
3. Гибридный recommendation engine фильтрует доступные активности и ранжирует их по нескольким факторам.
4. Пользователь получает 1–3 рекомендации с проверяемым объяснением.
5. После завершения активности навыки, траектория и рекомендации пересчитываются.
6. HR видит агрегированные дефициты, участие и случаи без доступного следующего шага.

## Архитектура

Проект строится как модульный монорепозиторий:

- `apps/api` — FastAPI, доменная логика, импорт данных, recommendation engine и LLM adapter;
- `apps/web` — Next.js, интерфейсы сотрудника и HR;
- `data/seed` — локальное размещение стартового датасета без изменения исходных файлов;
- `docs` — архитектура, план и инструкции;
- `tests` — сквозные fixtures и будущие end-to-end тесты.

Подробности: [архитектура](docs/ARCHITECTURE.md) и [план разработки](docs/PROJECT_PLAN.md).

## Быстрый старт

Целевой способ запуска всего приложения:

```bash
docker compose up --build
```

Перед первым запуском:

```bash
git clone https://github.com/BAITC-Hacks/hack-efa741b1-qaldy-ai.git
cd hack-efa741b1-qaldy-ai
cp .env.example .env
```

На Windows PowerShell вместо `cp`:

```powershell
Copy-Item .env.example .env
```

После запуска откройте `http://localhost:3000`. Первый vertical slice использует явно маркированный demo-профиль; подключение полного стартового kit выполняется следующим этапом. Правила размещения датасета описаны в [инструкции настройки](docs/SETUP.md).

## Планируемые адреса

- Web: `http://localhost:3000`
- API: `http://localhost:8000`
- OpenAPI: `http://localhost:8000/docs`
- Healthcheck: `http://localhost:8000/health`

## Документация

- [Архитектура](docs/ARCHITECTURE.md)
- [План разработки](docs/PROJECT_PLAN.md)
- [Настройка и запуск](docs/SETUP.md)
- [Контракт API-модуля](apps/api/README.md)
- [Контракт frontend-модуля](apps/web/README.md)
- [Размещение seed-данных](data/seed/README.md)

## Проверки без Docker

Backend:

```bash
cd apps/api
python -m venv .venv
pip install -e ".[dev]"
pytest
```

Frontend:

```bash
cd apps/web
npm ci
npm run typecheck
npm run build
```

## Статус

Работает первый пользовательский сценарий: API отдаёт demo-профиль с траекторией, дефицитами и тремя объяснимыми рекомендациями, а web отображает его с loading/error состояниями. HR и import представлены базовыми экранами для следующих этапов.
