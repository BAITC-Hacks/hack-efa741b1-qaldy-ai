# Заметки о деплое на Vercel

Основной воспроизводимый запуск проекта — Docker Compose из корня репозитория. Vercel-настройки находятся вне Git и могут измениться; адреса ниже были записаны в проектных заметках, но их доступность здесь не проверена.

| Часть | Ранее указанный URL |
| --- | --- |
| Web | `https://hack-efa741b1-qaldy-ai.vercel.app` |
| API | `https://qaldy-ai-api.vercel.app` |

Перед демо проверьте URL, Git integration, SSO и переменные в Vercel dashboard. Frontend получает API URL через `NEXT_PUBLIC_API_URL`; API — дополнительные разрешённые origins через `CORS_ORIGINS`. Backend entrypoint проекта — корневой `index.py`, зависимости — `requirements.txt`.

## Авторизация и данные

Vercel runtime требует настроенных `DEMO_HR_TOKEN` и/или `DEMO_EMPLOYEE_TOKENS`. Для demo-auth в `VERCEL` окружении код требует явное `ALLOW_INSECURE_DEMO_AUTH=true`; используйте это только если Vercel доступ ограничен SSO, и только с синтетическим датасетом. Не публикуйте demo API открыто и не используйте реальные пользовательские данные.

Приложение сохраняет завершения и импорты в SQLite по `DATABASE_URL`. Репозиторий не подключает к Vercel общую постоянную базу данных или диск; локальный SQLite-файл в serverless-функции не гарантирует доступность данных в следующем запросе/экземпляре. Не демонстрируйте на Vercel сохранение состояния как надёжное. Для основного сценария с импортом и проверкой persistence используйте Docker Compose с volume.

Startup работает fail-closed: Vercel без явного `DATABASE_URL`, demo-токена и разрешения demo-auth не проходит readiness. `/livez` проверяет только процесс, а `/readyz` и legacy `/health` загружают dataset и выполняют DB query.

Для временного закрытого Vercel-demo минимальная конфигурация выглядит так:

```text
APP_ENV=production
AUTH_MODE=demo
ALLOW_INSECURE_DEMO_AUTH=true
DEMO_HR_TOKEN=<random secret of at least 16 characters>
DATABASE_URL=sqlite:////tmp/career_quest.db
CORS_ORIGINS=https://hack-efa741b1-qaldy-ai.vercel.app
```

Этот режим остаётся недолговечным. Перед публичным backend-деплоем обязательны PostgreSQL repository + migrations, транзакционный `active_dataset_version`, object-storage quarantine для imports, OIDC/JWT и раздельные Preview/Production данные. До этого API должен оставаться за Vercel SSO.

`LLM_ENABLED` выключен по умолчанию. Для AI-reranking `LLM_API_KEY` храните только в Vercel Secret/Environment Variables, не в репозитории.

Локальный успешный запуск не подтверждает успешный Vercel deployment. Перед его использованием вручную проверьте web, `/readyz` API, авторизацию токеном, CORS и фактическую сохранность данных.
