# Cross-application tests

Каталог зарезервирован для общих fixtures и сквозных тестов, не принадлежащих только API или web. Сейчас в нём нет исполняемых cross-application тестов. Playwright E2E в `apps/web/tests` использует web fixtures и не поднимает живой FastAPI, поэтому не проверяет интеграцию двух сервисов.

Предлагаемый smoke-сценарий:

`открыть сотрудника → получить рекомендации → завершить активность → увидеть обновлённый прогресс`.

Backend-тесты находятся в `apps/api/tests`, frontend unit-тесты — в `apps/web/src` рядом с модулями, Playwright E2E — в `apps/web/tests`.
