import {
  DEMO_STATE_VERSION,
  type AiMessage,
  type DemoState,
  type DemoTabs,
  type PersistedDemoStateV1,
  type StorageLike,
  type VisibilitySettings,
} from "./types";

export const DEMO_STORAGE_KEY = "qaldy-career-quest:demo:v1";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function isOneOf<T extends string>(value: unknown, options: readonly T[]): value is T {
  return typeof value === "string" && options.includes(value as T);
}

function parseTabs(value: unknown): DemoTabs | null {
  if (!isRecord(value)) return null;
  if (
    !isOneOf(value.quests, ["all", "active", "available", "completed"] as const) ||
    !isOneOf(value.learning, ["recommended", "in_progress", "saved", "completed"] as const) ||
    !isOneOf(value.opportunities, ["all", "vacancy", "project", "mentoring", "rotation"] as const) ||
    !isOneOf(value.library, ["all", "article", "book", "video", "template", "saved", "recent"] as const)
  ) {
    return null;
  }
  return {
    quests: value.quests,
    learning: value.learning,
    opportunities: value.opportunities,
    library: value.library,
  };
}

function parseVisibility(value: unknown): VisibilitySettings | null {
  if (!isRecord(value)) return null;
  const allowed = ["team", "company", "private"] as const;
  if (
    !isOneOf(value.profile, allowed) ||
    !isOneOf(value.skills, allowed) ||
    !isOneOf(value.achievements, allowed)
  ) {
    return null;
  }
  return {
    profile: value.profile,
    skills: value.skills,
    achievements: value.achievements,
  };
}

function parseAiMessage(value: unknown): AiMessage | null {
  if (!isRecord(value)) return null;
  if (
    typeof value.id !== "string" ||
    !isOneOf(value.role, ["user", "assistant"] as const) ||
    typeof value.content !== "string" ||
    typeof value.createdAt !== "string" ||
    value.id.length > 160 ||
    value.content.length > 20_000 ||
    value.createdAt.length > 80
  ) {
    return null;
  }
  const feedback = isOneOf(value.feedback, ["like", "dislike"] as const)
    ? value.feedback
    : undefined;
  return {
    id: value.id,
    role: value.role,
    content: value.content,
    createdAt: value.createdAt,
    ...(feedback ? { feedback } : {}),
  };
}

export function parsePersistedDemoState(value: unknown): PersistedDemoStateV1 | null {
  if (!isRecord(value) || value.version !== DEMO_STATE_VERSION) return null;
  const selectedTabs = parseTabs(value.selectedTabs);
  const visibility = parseVisibility(value.visibility);
  if (
    !selectedTabs ||
    !visibility ||
    !isStringArray(value.savedCourseIds) ||
    !isStringArray(value.savedOpportunityIds) ||
    !isStringArray(value.appliedOpportunityIds) ||
    !isStringArray(value.savedResourceIds) ||
    !Array.isArray(value.aiMessages)
  ) {
    return null;
  }
  const aiMessages = value.aiMessages.map(parseAiMessage);
  if (aiMessages.some((message) => message === null)) return null;

  return {
    version: DEMO_STATE_VERSION,
    savedCourseIds: [...new Set(value.savedCourseIds)],
    savedOpportunityIds: [...new Set(value.savedOpportunityIds)],
    appliedOpportunityIds: [...new Set(value.appliedOpportunityIds)],
    savedResourceIds: [...new Set(value.savedResourceIds)],
    selectedTabs,
    aiMessages: (aiMessages as AiMessage[]).slice(-100),
    visibility,
  };
}

export function toPersistedDemoState(state: DemoState): PersistedDemoStateV1 {
  return {
    version: DEMO_STATE_VERSION,
    savedCourseIds: state.learning.filter((item) => item.saved).map((item) => item.id),
    savedOpportunityIds: state.opportunities.filter((item) => item.saved).map((item) => item.id),
    appliedOpportunityIds: state.opportunities.filter((item) => item.applied).map((item) => item.id),
    savedResourceIds: state.library.filter((item) => item.saved).map((item) => item.id),
    selectedTabs: state.selectedTabs,
    aiMessages: state.aiMessages.slice(-100),
    visibility: state.user.visibility,
  };
}

export function mergePersistedDemoState(
  base: DemoState,
  persisted: PersistedDemoStateV1,
): DemoState {
  const savedCourses = new Set(persisted.savedCourseIds);
  const savedOpportunities = new Set(persisted.savedOpportunityIds);
  const appliedOpportunities = new Set(persisted.appliedOpportunityIds);
  const savedResources = new Set(persisted.savedResourceIds);
  return {
    ...base,
    user: { ...base.user, visibility: persisted.visibility },
    learning: base.learning.map((item) => ({ ...item, saved: savedCourses.has(item.id) })),
    opportunities: base.opportunities.map((item) => ({
      ...item,
      saved: savedOpportunities.has(item.id),
      applied: appliedOpportunities.has(item.id),
    })),
    library: base.library.map((item) => ({ ...item, saved: savedResources.has(item.id) })),
    selectedTabs: persisted.selectedTabs,
    aiMessages: persisted.aiMessages,
  };
}

export function getBrowserStorage(): StorageLike | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export function loadDemoState(
  base: DemoState,
  storage: StorageLike | null = getBrowserStorage(),
  key = DEMO_STORAGE_KEY,
): DemoState {
  if (!storage) return base;
  try {
    const serialized = storage.getItem(key);
    if (!serialized) return base;
    const persisted = parsePersistedDemoState(JSON.parse(serialized) as unknown);
    if (!persisted) {
      storage.removeItem(key);
      return base;
    }
    return mergePersistedDemoState(base, persisted);
  } catch {
    return base;
  }
}

export function saveDemoState(
  state: DemoState,
  storage: StorageLike | null = getBrowserStorage(),
  key = DEMO_STORAGE_KEY,
): boolean {
  if (!storage) return false;
  try {
    storage.setItem(key, JSON.stringify(toPersistedDemoState(state)));
    return true;
  } catch {
    return false;
  }
}

export function clearPersistedDemoState(
  storage: StorageLike | null = getBrowserStorage(),
  key = DEMO_STORAGE_KEY,
): boolean {
  if (!storage) return false;
  try {
    storage.removeItem(key);
    return true;
  } catch {
    return false;
  }
}
