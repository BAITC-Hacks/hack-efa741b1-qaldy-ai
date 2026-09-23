export const DEMO_STATE_VERSION = 1 as const;
export const DEMO_AS_OF_DATE = "2026-09-23" as const;

export type IsoDate = `${number}-${number}-${number}`;
export type EntityId = string;

export type VisibilitySettings = {
  profile: "team" | "company" | "private";
  skills: "team" | "company" | "private";
  achievements: "team" | "company" | "private";
};

export type DemoUser = {
  id: EntityId;
  fullName: string;
  firstName: string;
  initials: string;
  role: string;
  grade: string;
  department: string;
  location: string;
  level: number;
  totalXp: number;
  streakDays: number;
  visibility: VisibilitySettings;
};

export type CareerGoal = {
  role: string;
  grade: string;
  targetDate: IsoDate;
  reason: string;
};

export type CareerNodeStatus = "completed" | "current" | "available" | "locked";

export type CareerNode = {
  id: EntityId;
  title: string;
  grade: string;
  status: CareerNodeStatus;
  parentIds: EntityId[];
  requirement: string;
};

export type SkillStatus = "mastered" | "developing" | "locked";
export type SkillEvidenceKind = "certificate" | "artifact" | "feedback";

export type SkillEvidence = {
  id: EntityId;
  title: string;
  kind: SkillEvidenceKind;
  verified: boolean;
  earnedAt?: IsoDate;
};

export type Skill = {
  id: EntityId;
  name: string;
  category: "professional" | "leadership" | "business" | "digital";
  currentLevel: number;
  targetLevel: number;
  maxLevel: number;
  readinessWeight: number;
  status: SkillStatus;
  relatedSkillIds: EntityId[];
  evidence: SkillEvidence[];
};

export type QuestStatus = "available" | "active" | "completed" | "locked";
export type QuestDisplayStatus = QuestStatus | "overdue";
export type QuestDifficulty = "easy" | "medium" | "hard";
export type QuestKind = "career" | "learning" | "team" | "practice";

export type QuestEvidence = {
  id: EntityId;
  label: string;
  completed: boolean;
  weight: number;
  completedAt?: IsoDate;
};

export type Quest = {
  id: EntityId;
  title: string;
  description: string;
  kind: QuestKind;
  difficulty: QuestDifficulty;
  status: QuestStatus;
  dueDate?: IsoDate;
  xpReward: number;
  skillIds: EntityId[];
  skillGain?: { skillId: EntityId; levels: number };
  progressPercent: number;
  evidence: QuestEvidence[];
  isPrimary: boolean;
};

export type LearningStatus = "recommended" | "in_progress" | "completed";
export type LearningFormat = "course" | "workshop" | "mentoring" | "webinar";

export type LearningItem = {
  id: EntityId;
  title: string;
  provider: string;
  description: string;
  format: LearningFormat;
  durationMinutes: number;
  status: LearningStatus;
  progressPercent: number;
  skillIds: EntityId[];
  saved: boolean;
  nextSessionAt?: string;
  readinessImpact: number;
};

export type Certificate = {
  id: EntityId;
  sourceLearningId: EntityId;
  title: string;
  issuer: string;
  issuedAt: IsoDate;
};

export type OpportunityKind = "vacancy" | "project" | "mentoring" | "rotation";

export type Opportunity = {
  id: EntityId;
  title: string;
  description: string;
  kind: OpportunityKind;
  department: string;
  location: string;
  matchPercent: number;
  skillIds: EntityId[];
  deadline?: IsoDate;
  saved: boolean;
  applied: boolean;
};

export type TeamMember = {
  id: EntityId;
  name: string;
  initials: string;
  publicRole: string;
  contribution: string;
};

export type HelpRequest = {
  id: EntityId;
  title: string;
  skillId: EntityId;
  authorName: string;
  status: "open" | "answered";
};

export type TeamMission = {
  id: EntityId;
  title: string;
  description: string;
  role: string;
  progressPercent: number;
  dueDate: IsoDate;
  linkedQuestId: EntityId;
  members: TeamMember[];
  helpRequests: HelpRequest[];
};

export type LibraryResourceKind = "article" | "book" | "video" | "template";

export type LibraryResource = {
  id: EntityId;
  title: string;
  description: string;
  author: string;
  kind: LibraryResourceKind;
  durationMinutes: number;
  tags: string[];
  skillIds: EntityId[];
  saved: boolean;
  lastViewedAt?: string;
};

export type Achievement = {
  id: EntityId;
  title: string;
  description: string;
  earnedAt: IsoDate;
  icon: "star" | "trophy" | "target" | "sparkles";
  xpAwarded: number;
};

export type PortfolioItem = {
  id: EntityId;
  title: string;
  description: string;
  kind: "project" | "document" | "presentation";
  createdAt: IsoDate;
};

export type AiSource = {
  id: EntityId;
  title: string;
  kind: "skill" | "quest" | "learning" | "opportunity";
  entityId: EntityId;
};

export type AiMessage = {
  id: EntityId;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  sources?: AiSource[];
  feedback?: "like" | "dislike";
};

export type AiPlanStep = {
  id: EntityId;
  title: string;
  description: string;
  status: "done" | "current" | "next";
  entityId?: EntityId;
};

export type AiPlan = {
  title: string;
  summary: string;
  projectedReadinessImpact: number;
  impactExplanation: string;
  steps: AiPlanStep[];
  alternativeRoute: {
    title: string;
    description: string;
    entityIds: EntityId[];
  };
};

export type DemoTabs = {
  quests: "all" | "active" | "available" | "completed";
  learning: "recommended" | "in_progress" | "saved" | "completed";
  opportunities: "all" | OpportunityKind;
  library: "all" | LibraryResourceKind | "saved" | "recent";
};

export type DemoState = {
  version: typeof DEMO_STATE_VERSION;
  asOfDate: typeof DEMO_AS_OF_DATE;
  user: DemoUser;
  goal: CareerGoal;
  careerNodes: CareerNode[];
  skills: Skill[];
  quests: Quest[];
  learning: LearningItem[];
  certificates: Certificate[];
  opportunities: Opportunity[];
  teamMission: TeamMission;
  library: LibraryResource[];
  achievements: Achievement[];
  portfolio: PortfolioItem[];
  aiMessages: AiMessage[];
  aiPlan: AiPlan;
  selectedTabs: DemoTabs;
};

export type PersistedDemoStateV1 = {
  version: typeof DEMO_STATE_VERSION;
  savedCourseIds: EntityId[];
  savedOpportunityIds: EntityId[];
  appliedOpportunityIds: EntityId[];
  savedResourceIds: EntityId[];
  selectedTabs: DemoTabs;
  aiMessages: AiMessage[];
  visibility: VisibilitySettings;
};

export type StorageLike = Pick<Storage, "getItem" | "setItem" | "removeItem">;
