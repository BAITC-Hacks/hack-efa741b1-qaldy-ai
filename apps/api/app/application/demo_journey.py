from app.domain.journey import (
    EmployeeJourney,
    EmployeeSummary,
    Recommendation,
    SkillGap,
)


def get_demo_employee_journey() -> EmployeeJourney:
    """Return a transparent demo response until the dataset importer lands."""
    return EmployeeJourney(
        source="demo",
        employee=EmployeeSummary(
            employee_id="DEMO-001",
            full_name="Марат Есенов",
            role="Backend Engineer",
            grade="Middle",
            target_role="Backend Engineer",
            target_grade="Senior",
            trajectory_progress=68,
        ),
        skill_gaps=[
            SkillGap(
                skill_id="SK_SYSTEM_DESIGN",
                name="System Design",
                current_level=2,
                required_level=4,
                critical=True,
            ),
            SkillGap(
                skill_id="SK_API_DESIGN",
                name="API Design",
                current_level=3,
                required_level=4,
                critical=True,
            ),
            SkillGap(
                skill_id="SK_PUBLIC_SPEAKING",
                name="Public Speaking",
                current_level=2,
                required_level=3,
                critical=False,
            ),
        ],
        recommendations=[
            Recommendation(
                event_id="EV_006",
                title="Designing High-Load Systems",
                format="online",
                duration_hours=16,
                score=92,
                skill="System Design",
                current_level=2,
                projected_level=3,
                required_level=4,
                reasons=[
                    "System Design — критичный навык для перехода на Senior.",
                    "Активность сокращает разрыв с 2 уровней до 1.",
                    "Онлайн-формат соответствует успешной истории прохождения курсов.",
                ],
            ),
            Recommendation(
                event_id="EV_007",
                title="Architecture Review Circle",
                format="offline",
                duration_hours=6,
                score=84,
                skill="System Design",
                current_level=2,
                projected_level=3,
                required_level=4,
                reasons=[
                    "Закрывает критичный разрыв целевого грейда Senior.",
                    "Короткий практический формат дополняет основной курс.",
                    "Предварительные требования выполнены текущим уровнем навыка.",
                ],
            ),
            Recommendation(
                event_id="EV_040",
                title="Structured Problem Solving",
                format="offline",
                duration_hours=4,
                score=71,
                skill="Problem Solving",
                current_level=3,
                projected_level=4,
                required_level=4,
                reasons=[
                    "Поддерживает требования следующего грейда.",
                    "Полностью закрывает разрыв по Problem Solving.",
                    "Небольшая длительность делает шаг реалистичным в ближайшем цикле.",
                ],
            ),
        ],
    )
