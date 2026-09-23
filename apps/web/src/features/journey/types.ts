export type EmployeeSummary = {
  employee_id: string;
  full_name: string;
  role: string;
  grade: string;
  target_role: string;
  target_grade: string;
  trajectory_progress: number;
};

export type SkillGap = {
  skill_id: string;
  name: string;
  current_level: number;
  required_level: number;
  critical: boolean;
};

export type Recommendation = {
  event_id: string;
  title: string;
  format: "online" | "offline" | "self_paced";
  duration_hours: number;
  score: number;
  skill: string;
  current_level: number;
  projected_level: number;
  required_level: number;
  reasons: string[];
};

export type EmployeeJourney = {
  source: "demo" | "dataset";
  employee: EmployeeSummary;
  skill_gaps: SkillGap[];
  recommendations: Recommendation[];
};
