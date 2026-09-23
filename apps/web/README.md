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

Текущий vertical slice загружает demo journey из FastAPI и показывает профиль, траекторию, дефициты и три объяснимых шага.

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
