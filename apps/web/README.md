# Web-приложение

Next.js-приложение содержит основной интерфейс сотрудника, HR-аналитику и страницу импорта проверочных профилей. Интерфейс получает данные основного сценария и HR из FastAPI. Страницы обучения, команды и некоторых других концептов остаются демонстрационными и могут использовать локальные данные.

Основные маршруты:

- `/journey` — траектория сотрудника, разрывы навыков, рекомендации и завершение активности;
- `/` — главная страница с демо-содержимым;
- `/hr` — вкладки HR-метрик из `/api/v1/hr/*`;
- `/import` — загрузка JSON и необязательного CSV, вызовы `/api/v1/import/validate` и `/api/v1/import/apply`.

Подробности bearer-доступа и формата импорта — в [`../../docs/API.md`](../../docs/API.md). Для локального демо введите выданный сервером токен через меню профиля. Токен хранится в `sessionStorage` текущей вкладки; demo-доступ не является production-аутентификацией.

## Запуск

Требуется Node.js 22.x.

```bash
npm ci
npm run dev
```

Для работы employee и HR экранов запустите также API из корня проекта через Docker Compose либо отдельно по [`../api/README.md`](../api/README.md). При отдельном запуске адрес API задаётся через `NEXT_PUBLIC_API_URL`.

## Проверки

```bash
npm run lint
npm run typecheck
npm test
npm run build
npx playwright install chromium
npm run test:e2e
```

Playwright E2E создаёт production-сборку и запускает Next.js с web fixtures. Это не проверка интеграции с живым API. Visual и accessibility suites запускаются отдельно командами `npm run test:visual` и `npm run test:a11y`; им также требуется браузер Playwright.
