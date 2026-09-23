export type EmployeeListItem = {
  employee_id: string;
  full_name: string;
  department: string;
  role: string;
  grade: string;
};

export type Employee = EmployeeListItem & {
  work_format: string;
  preferred_language: string;
};

export type Progress = {
  current_points: number;
  required_points: number;
  percentage: number;
};

export type SkillGap = {
  skill_id: string;
  name: string;
  current_level: number;
  required_level: number;
  gap: number;
  critical: boolean;
};

export type FactorScore = {
  code: string;
  label: string;
  value: number;
  weight: number;
  contribution: number;
};

export type Recommendation = {
  event_id: string;
  title: string;
  event_format: "online" | "offline" | "self_paced";
  duration_hours: number;
  score: number;
  kind: "current_role" | "bridge";
  skill: string;
  current_level: number;
  projected_level: number;
  required_level: number;
  reasons: string[];
  factors: FactorScore[];
};

export type Continuation = {
  event_id: string;
  title: string;
  completion_pct: number;
};

export type EmployeeJourney = {
  source: "dataset";
  dataset_version: string;
  as_of_date: string;
  employee: Employee;
  target_role: string;
  target_grade: string;
  target_reason: string;
  progress: Progress;
  skill_gaps: SkillGap[];
  recommendations: Recommendation[];
  continuations: Continuation[];
  recommendation_mode: "deterministic" | "ai";
  recommendation_notice: string | null;
  primary_reason: string | null;
  reason_counts: Record<string, number>;
};

export type SkillChange = {
  skill_id: string;
  name: string;
  before: number;
  after: number;
  applied_gain: number;
};

export type CompletionResult = {
  record_id: string;
  idempotent_replay: boolean;
  changes: SkillChange[];
  journey: EmployeeJourney;
};
