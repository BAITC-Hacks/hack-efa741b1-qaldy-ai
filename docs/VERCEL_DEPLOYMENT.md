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

`LLM_ENABLED` выключен по умолчанию. Для AI-reranking `LLM_API_KEY` храните только в Vercel Secret/Environment Variables, не в репозитории.

Локальный успешный запуск не подтверждает успешный Vercel deployment. Перед его использованием вручную проверьте web, `/readyz` API, авторизацию токеном, CORS и фактическую сохранность данных.
