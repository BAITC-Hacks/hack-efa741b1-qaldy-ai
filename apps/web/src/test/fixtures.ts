import type {
  CompletionResult,
  EmployeeJourney,
  EmployeeListItem,
} from "@/features/journey/types";

export const employeeFixture: EmployeeListItem = {
  employee_id: "employee-demo",
  full_name: "Марат Есенов",
  department: "Цифровые продукты",
  role: "Product Analyst",
  grade: "Middle",
};

export const journeyFixture: EmployeeJourney = {
  source: "dataset",
  dataset_version: "e2e-2026-09-23",
  as_of_date: "2026-09-23",
  employee: {
    ...employeeFixture,
    work_format: "hybrid",
    preferred_language: "ru",
  },
  target_role: "Senior Product Manager",
  target_grade: "Senior",
  target_reason: "Следующий подтверждённый карьерный шаг",
  progress: {
    current_points: 72,
    required_points: 100,
    percentage: 72,
  },
  current_skills: [
    { skill_id: "sql", name: "SQL", level: 4 },
    { skill_id: "strategy", name: "Продуктовая стратегия", level: 3 },
    { skill_id: "leadership", name: "Лидерство", level: 4 },
  ],
  skill_gaps: [
    {
      skill_id: "strategy",
      name: "Продуктовая стратегия",
      current_level: 3,
      required_level: 5,
      gap: 2,
      critical: true,
    },
    {
      skill_id: "leadership",
      name: "Лидерство",
      current_level: 4,
      required_level: 5,
      gap: 1,
      critical: false,
    },
  ],
  recommendations: [
    {
      event_id: "quest-strategy",
      title: "Сформировать стратегию продукта",
      event_format: "self_paced",
      duration_hours: 8,
      score: 0.94,
      kind: "bridge",
      skill: "Продуктовая стратегия",
      current_level: 3,
      projected_level: 4,
      required_level: 5,
      reasons: ["Закрывает критический разрыв"],
      factors: [
        {
          code: "skill_gap",
          label: "Разрыв навыка",
          value: 2,
          weight: 0.6,
          contribution: 1.2,
        },
      ],
    },
  ],
  continuations: [
    {
      event_id: "course-research",
      title: "Исследования клиентов",
      completion_pct: 60,
    },
  ],
  activity_history: [
    {
      record_id: "activity-completed-1",
      event_id: "customer-discovery",
      title: "Customer Discovery Lab",
      activity_date: "2026-08-14",
      due_date: "2026-08-31",
      status: "completed",
      completion_pct: 100,
      score: 91,
      feedback_rating: 5,
      assigned_by: "self",
      source: "seed",
    },
    {
      record_id: "activity-progress-1",
      event_id: "course-research",
      title: "Исследования клиентов",
      activity_date: "2026-09-10",
      due_date: null,
      status: "in_progress",
      completion_pct: 60,
      score: null,
      feedback_rating: null,
      assigned_by: "self",
      source: "seed",
    },
  ],
  recommendation_mode: "deterministic",
  recommendation_notice: null,
  primary_reason: "skill_gap",
  reason_counts: { skill_gap: 1 },
};

export const completionFixture: CompletionResult = {
  record_id: "completion-demo",
  idempotent_replay: false,
  changes: [
    {
      skill_id: "strategy",
      name: "Продуктовая стратегия",
      before: 3,
      after: 4,
      applied_gain: 1,
    },
  ],
  journey: {
    ...journeyFixture,
    progress: {
      current_points: 80,
      required_points: 100,
      percentage: 80,
    },
  },
};
