# Происхождение HR-показателей

Источник реализации: `apps/api/app/application/hr_service.py` (HRService) и `journey_service.py` (JourneyService). Срез ответа содержит `dataset_version`, `as_of_date`, `filters`, `employee_count`. Фильтры department/role/grade применяются до агрегации. Данные — seed плюс применённый импорт и runtime-завершения SQLite; история дедуплицируется по `record_id`.

Для каждого сотрудника используется тот же `get_journey`, что и в профиле. Текущий навык — исходная оценка плюс завершения строго после `last_review_date`, с пределами события и общей шкалы. Разрыв `gap = max(0, required_level - current_level)`; нулевые разрывы не включаются.

`/api/v1/hr/skill-gaps`: `affected_employees` — число сотрудников с положительным разрывом по навыку; `total_gap` — сумма этих разрывов; `average_gap` — total_gap/affected_employees, округление до двух знаков; `critical_employees` — сколько из этих сотрудников имеют навык в critical_skills целевого профиля. Сортировка: сначала critical_employees, затем affected_employees и total_gap по убыванию, затем skill_id по возрастанию. Это ранжирование потребностей навыков, не сотрудников.

`/api/v1/hr/uncovered-employees`: включает сотрудника ровно тогда, когда его текущий journey не имеет рекомендаций. Причина и счётчики отсева берутся из того же journey. Отсутствие рекомендации не означает низкую результативность: возможны выполненные требования или пробел каталога.

`/api/v1/hr/participation`: `total_records` — число строк истории после фильтра; `participating_employees` — число уникальных employee_id в них. Счётчики статусов не смешивают completed/no_show/declined/in_progress/dropped/overdue. `by_event` и `by_type` группируют строки по event_id и типу события. `completion_rate = completed / total`, округление до четырёх знаков, при нуле строк —0. Повторяемое событие может дать несколько строк одного сотрудника; знаменатель относится к участию, не к числу людей.

Для проверки конкретного числа HR может запросить соответствующий API с теми же фильтрами и сопоставить положительные разрывы с journey выбранных сотрудников либо строки истории с группами event_id/status. Доступ регулируется HR Bearer-токеном; сотруднику эти агрегаты не выдаются.
