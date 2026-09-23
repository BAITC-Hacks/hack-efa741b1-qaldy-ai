import type {
  DemoState,
  LearningFormat,
  LearningItem,
  LibraryResource,
  LibraryResourceKind,
  Opportunity,
  OpportunityKind,
  Quest,
  QuestDifficulty,
  QuestDisplayStatus,
  QuestKind,
  Skill,
} from "./types";

export type XpProgress = {
  level: number;
  totalXp: number;
  currentLevelXp: number;
  nextLevelXp: number;
  requiredForNextLevel: number;
  percentage: number;
};

export type SkillGap = {
  skillId: string;
  name: string;
  currentLevel: number;
  targetLevel: number;
  gap: number;
  weightedGap: number;
};

export type QuestFilters = {
  query?: string;
  tab?: "all" | "active" | "available" | "completed";
  kind?: QuestKind | "all";
  difficulty?: QuestDifficulty | "all";
  skillId?: string | "all";
  overdueOnly?: boolean;
};

export type LearningFilters = {
  query?: string;
  tab?: "recommended" | "in_progress" | "saved" | "completed" | "all";
  format?: LearningFormat | "all";
  skillId?: string | "all";
  maxDurationMinutes?: number;
};

export type OpportunityFilters = {
  query?: string;
  kind?: OpportunityKind | "all";
  skillId?: string | "all";
  location?: string | "all";
  savedOnly?: boolean;
  appliedOnly?: boolean;
  minimumMatch?: number;
};

export type LibraryFilters = {
  query?: string;
  kind?: LibraryResourceKind | "all";
  skillId?: string | "all";
  tag?: string | "all";
  savedOnly?: boolean;
  recentOnly?: boolean;
};

export function clamp(value: number, minimum = 0, maximum = 100): number {
  if (!Number.isFinite(value)) return minimum;
  return Math.min(maximum, Math.max(minimum, value));
}

export function normalizeSearch(value: string): string {
  return value
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase("ru-RU")
    .replace(/[\u0451]/g, "е")
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim();
}

export function matchesSearch(query: string | undefined, values: readonly string[]): boolean {
  const normalizedQuery = normalizeSearch(query ?? "");
  if (!normalizedQuery) return true;
  const haystack = normalizeSearch(values.join(" "));
  return normalizedQuery.split(/\s+/).every((token) => haystack.includes(token));
}

export function searchByText<T>(
  items: readonly T[],
  query: string | undefined,
  project: (item: T) => readonly string[],
): T[] {
  return items.filter((item) => matchesSearch(query, project(item)));
}

export function calculateXpProgress(totalXp: number, xpPerLevel = 1_000): XpProgress {
  const safeTotal = Math.max(0, Math.floor(Number.isFinite(totalXp) ? totalXp : 0));
  const safeLevelSize = Math.max(1, Math.floor(Number.isFinite(xpPerLevel) ? xpPerLevel : 1_000));
  const completedLevels = Math.floor(safeTotal / safeLevelSize);
  const currentLevelXp = safeTotal - completedLevels * safeLevelSize;

  return {
    level: completedLevels + 1,
    totalXp: safeTotal,
    currentLevelXp,
    nextLevelXp: (completedLevels + 1) * safeLevelSize,
    requiredForNextLevel: safeLevelSize,
    percentage: clamp(Math.round((currentLevelXp / safeLevelSize) * 100)),
  };
}

/** Readiness is the weighted fulfillment of target skill levels, always 0..100. */
export function calculateReadiness(skills: readonly Skill[]): number {
  const relevant = skills.filter(
    (skill) => skill.targetLevel > 0 && Number.isFinite(skill.readinessWeight) && skill.readinessWeight > 0,
  );
  const totalWeight = relevant.reduce((sum, skill) => sum + skill.readinessWeight, 0);
  if (totalWeight === 0) return 0;

  const score = relevant.reduce((sum, skill) => {
    const fulfillment = clamp(skill.currentLevel / skill.targetLevel, 0, 1);
    return sum + fulfillment * skill.readinessWeight;
  }, 0);

  return clamp(Math.round((score / totalWeight) * 100));
}

export function selectSkillGaps(skills: readonly Skill[]): SkillGap[] {
  return skills
    .map((skill) => {
      const gap = Math.max(0, skill.targetLevel - skill.currentLevel);
      return {
        skillId: skill.id,
        name: skill.name,
        currentLevel: skill.currentLevel,
        targetLevel: skill.targetLevel,
        gap,
        weightedGap: gap * Math.max(0, skill.readinessWeight),
      };
    })
    .filter((gap) => gap.gap > 0)
    .sort((left, right) => right.weightedGap - left.weightedGap || left.name.localeCompare(right.name, "ru"));
}

export function calculateQuestProgress(evidence: Quest["evidence"]): number {
  const totalWeight = evidence.reduce((sum, item) => sum + Math.max(0, item.weight), 0);
  if (totalWeight === 0) return evidence.length === 0 ? 0 : clamp(
    Math.round((evidence.filter((item) => item.completed).length / evidence.length) * 100),
  );
  const completedWeight = evidence.reduce(
    (sum, item) => sum + (item.completed ? Math.max(0, item.weight) : 0),
    0,
  );
  return clamp(Math.round((completedWeight / totalWeight) * 100));
}

function dateKey(value: string): string | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
  return match ? `${match[1]}-${match[2]}-${match[3]}` : null;
}

export function isOverdue(dueDate: string | undefined, asOfDate: string): boolean {
  if (!dueDate) return false;
  const due = dateKey(dueDate);
  const asOf = dateKey(asOfDate);
  return due !== null && asOf !== null && due < asOf;
}

export function getQuestDisplayStatus(quest: Quest, asOfDate: string): QuestDisplayStatus {
  if (quest.status === "active" && isOverdue(quest.dueDate, asOfDate)) return "overdue";
  return quest.status;
}

/**
 * Combines overlapping readiness effects and applies a product cap. This avoids
 * presenting several projections as naively additive.
 */
export function calculateNonAdditiveImpact(
  impacts: readonly number[],
  maximumImpact = 100,
): number {
  const remaining = impacts.reduce(
    (product, impact) => product * (1 - clamp(impact) / 100),
    1,
  );
  return clamp(Math.round(Math.min(maximumImpact, (1 - remaining) * 100)));
}

export function calculateProjectedReadiness(
  readiness: number,
  impacts: readonly number[],
  maximumImpact = 100,
): number {
  return clamp(readiness + calculateNonAdditiveImpact(impacts, maximumImpact));
}

function skillNameLookup(skills: readonly Skill[]): Map<string, string> {
  return new Map(skills.map((skill) => [skill.id, skill.name]));
}

function entitySkillNames(skillIds: readonly string[], names: ReadonlyMap<string, string>): string[] {
  return skillIds.map((id) => names.get(id) ?? id);
}

export function filterQuests(
  quests: readonly Quest[],
  filters: QuestFilters = {},
  asOfDate: string,
  skills: readonly Skill[] = [],
): Quest[] {
  const names = skillNameLookup(skills);
  return quests.filter((quest) => {
    const displayStatus = getQuestDisplayStatus(quest, asOfDate);
    const tabMatches =
      !filters.tab ||
      filters.tab === "all" ||
      (filters.tab === "active" ? displayStatus === "active" || displayStatus === "overdue" : quest.status === filters.tab);
    return (
      tabMatches &&
      (!filters.kind || filters.kind === "all" || quest.kind === filters.kind) &&
      (!filters.difficulty || filters.difficulty === "all" || quest.difficulty === filters.difficulty) &&
      (!filters.skillId || filters.skillId === "all" || quest.skillIds.includes(filters.skillId)) &&
      (!filters.overdueOnly || displayStatus === "overdue") &&
      matchesSearch(filters.query, [
        quest.title,
        quest.description,
        quest.kind,
        quest.difficulty,
        ...entitySkillNames(quest.skillIds, names),
      ])
    );
  });
}

export function filterLearning(
  items: readonly LearningItem[],
  filters: LearningFilters = {},
  skills: readonly Skill[] = [],
): LearningItem[] {
  const names = skillNameLookup(skills);
  return items.filter((item) => {
    const tabMatches =
      !filters.tab ||
      filters.tab === "all" ||
      (filters.tab === "saved" ? item.saved : item.status === filters.tab);
    return (
      tabMatches &&
      (!filters.format || filters.format === "all" || item.format === filters.format) &&
      (!filters.skillId || filters.skillId === "all" || item.skillIds.includes(filters.skillId)) &&
      (filters.maxDurationMinutes === undefined || item.durationMinutes <= filters.maxDurationMinutes) &&
      matchesSearch(filters.query, [
        item.title,
        item.provider,
        item.description,
        item.format,
        ...entitySkillNames(item.skillIds, names),
      ])
    );
  });
}

export function filterOpportunities(
  items: readonly Opportunity[],
  filters: OpportunityFilters = {},
  skills: readonly Skill[] = [],
): Opportunity[] {
  const names = skillNameLookup(skills);
  const location = normalizeSearch(filters.location ?? "");
  return items
    .filter((item) =>
      (!filters.kind || filters.kind === "all" || item.kind === filters.kind) &&
      (!filters.skillId || filters.skillId === "all" || item.skillIds.includes(filters.skillId)) &&
      (!location || location === "all" || normalizeSearch(item.location) === location) &&
      (!filters.savedOnly || item.saved) &&
      (!filters.appliedOnly || item.applied) &&
      (filters.minimumMatch === undefined || item.matchPercent >= filters.minimumMatch) &&
      matchesSearch(filters.query, [
        item.title,
        item.description,
        item.department,
        item.location,
        item.kind,
        ...entitySkillNames(item.skillIds, names),
      ]),
    )
    .sort((left, right) => right.matchPercent - left.matchPercent || left.title.localeCompare(right.title, "ru"));
}

export function filterLibrary(
  items: readonly LibraryResource[],
  filters: LibraryFilters = {},
  skills: readonly Skill[] = [],
): LibraryResource[] {
  const names = skillNameLookup(skills);
  const tag = normalizeSearch(filters.tag ?? "");
  return items
    .filter((item) =>
      (!filters.kind || filters.kind === "all" || item.kind === filters.kind) &&
      (!filters.skillId || filters.skillId === "all" || item.skillIds.includes(filters.skillId)) &&
      (!tag || tag === "all" || item.tags.some((candidate) => normalizeSearch(candidate) === tag)) &&
      (!filters.savedOnly || item.saved) &&
      (!filters.recentOnly || Boolean(item.lastViewedAt)) &&
      matchesSearch(filters.query, [
        item.title,
        item.description,
        item.author,
        item.kind,
        ...item.tags,
        ...entitySkillNames(item.skillIds, names),
      ]),
    )
    .sort((left, right) => {
      if (!filters.recentOnly) return left.title.localeCompare(right.title, "ru");
      return (right.lastViewedAt ?? "").localeCompare(left.lastViewedAt ?? "");
    });
}

export function formatDateRu(value: string, options?: Intl.DateTimeFormatOptions): string {
  const key = dateKey(value);
  if (!key) return "—";
  const date = new Date(`${key}T12:00:00.000Z`);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
    ...options,
  }).format(date);
}

export function formatDuration(minutes: number): string {
  const safeMinutes = Math.max(0, Math.round(Number.isFinite(minutes) ? minutes : 0));
  const hours = Math.floor(safeMinutes / 60);
  const remainder = safeMinutes % 60;
  if (hours === 0) return `${remainder} мин`;
  if (remainder === 0) return `${hours} ч`;
  return `${hours} ч ${remainder} мин`;
}

export function selectReadiness(state: DemoState): number {
  return calculateReadiness(state.skills);
}

export function selectPrimaryQuest(state: DemoState): Quest | undefined {
  return state.quests.find((quest) => quest.isPrimary);
}

export function selectDashboardStats(state: DemoState) {
  const statuses = state.quests.map((quest) => getQuestDisplayStatus(quest, state.asOfDate));
  return {
    readiness: selectReadiness(state),
    completedQuests: statuses.filter((status) => status === "completed").length,
    activeQuests: statuses.filter((status) => status === "active" || status === "overdue").length,
    availableQuests: statuses.filter((status) => status === "available").length,
    overdueQuests: statuses.filter((status) => status === "overdue").length,
    savedCourses: state.learning.filter((item) => item.saved).length,
    savedOpportunities: state.opportunities.filter((item) => item.saved).length,
    savedResources: state.library.filter((item) => item.saved).length,
    xp: calculateXpProgress(state.user.totalXp),
  };
}

export function selectRecommendedOpportunity(state: DemoState): Opportunity | undefined {
  return [...state.opportunities]
    .filter((item) => !item.applied)
    .sort((left, right) => right.matchPercent - left.matchPercent)[0];
}
