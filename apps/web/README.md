# Web application

Next.js-приложение с интерфейсами сотрудника и HR.

Структура:

```text
src/
├── app/          страницы employee, HR и import
├── components/   общая навигация
├── features/     employee journey и API client
├── i18n/         будущая локализация
└── lib/          общие утилиты
```

Страница сотрудника получает journey и рекомендации из FastAPI; страница `/hr` использует HR endpoints. Часть остальных product-концептов отображает локальные демонстрационные данные. Страница `/import` пока не может выполнить импорт: API `/api/v1/import/*` не реализован. Подробности — в [`../../docs/API.md`](../../docs/API.md).

Локальный запуск:

```bash
npm ci
npm run dev
```

Проверки:

```bash
npm run typecheck
npm run build
```

Также доступны `npm test`, `npm run lint`, `npm run test:e2e`, `npm run test:visual` и `npm run test:a11y`. Playwright scripts требуют настроенного browser/runtime; `npm run test:ci` запускает полный набор проверок.
