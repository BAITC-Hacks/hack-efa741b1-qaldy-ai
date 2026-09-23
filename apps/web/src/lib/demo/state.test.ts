import { describe, expect, it, vi } from "vitest";
import { createDemoState } from "./fixtures";
import {
  clearPersistedDemoState,
  DEMO_STORAGE_KEY,
  loadDemoState,
  mergePersistedDemoState,
  parsePersistedDemoState,
  saveDemoState,
  toPersistedDemoState,
} from "./persistence";
import { demoReducer } from "./reducer";
import { createDemoStore } from "./store";
import { DEMO_STATE_VERSION, type StorageLike } from "./types";

function memoryStorage(): StorageLike & { values: Map<string, string> } {
  const values = new Map<string, string>();
  return {
    values,
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => void values.set(key, value),
    removeItem: (key) => void values.delete(key),
  };
}

describe("demoReducer", () => {
  it("updates bookmark, application, recent-resource and tab state immutably", () => {
    let state = createDemoState();
    const original = state;
    state = demoReducer(state, { type: "toggle-course-saved", learningId: "learning-project-leadership" });
    state = demoReducer(state, { type: "toggle-opportunity-saved", opportunityId: "opportunity-pm-vacancy" });
    state = demoReducer(state, { type: "apply-to-opportunity", opportunityId: "opportunity-pm-vacancy" });
    state = demoReducer(state, { type: "toggle-resource-saved", resourceId: "resource-pm-book" });
    state = demoReducer(state, {
      type: "mark-resource-viewed",
      resourceId: "resource-pm-book",
      viewedAt: "2026-09-23T12:00:00+05:00",
    });
    state = demoReducer(state, { type: "set-tab", section: "quests", value: "active" });
    expect(state).not.toBe(original);
    expect(state.learning.find((item) => item.id === "learning-project-leadership")?.saved).toBe(true);
    expect(state.opportunities.find((item) => item.id === "opportunity-pm-vacancy")).toMatchObject({
      saved: true,
      applied: true,
    });
    expect(state.library.find((item) => item.id === "resource-pm-book")).toMatchObject({
      saved: true,
      lastViewedAt: "2026-09-23T12:00:00+05:00",
    });
    expect(state.selectedTabs.quests).toBe("active");
  });

  it("starts available quests and converts explicit progress to in-progress learning", () => {
    let state = createDemoState();
    state = demoReducer(state, { type: "start-quest", questId: "quest-strategy-case" });
    state = demoReducer(state, {
      type: "set-course-progress",
      learningId: "learning-project-leadership",
      progressPercent: 125,
    });
    expect(state.quests.find((item) => item.id === "quest-strategy-case")?.status).toBe("active");
    expect(state.learning.find((item) => item.id === "learning-project-leadership")).toMatchObject({
      status: "in_progress",
      progressPercent: 100,
    });
  });

  it("completes a course with exactly one certificate", () => {
    const initial = createDemoState();
    const once = demoReducer(initial, {
      type: "complete-course",
      learningId: "learning-strategic-thinking",
      completedAt: "2026-09-23T20:00:00+05:00",
    });
    const twice = demoReducer(once, {
      type: "complete-course",
      learningId: "learning-strategic-thinking",
    });
    expect(twice.learning.find((item) => item.id === "learning-strategic-thinking")).toMatchObject({
      status: "completed",
      progressPercent: 100,
    });
    expect(
      twice.certificates.filter((item) => item.sourceLearningId === "learning-strategic-thinking"),
    ).toHaveLength(1);
  });

  it("turns 2/3 evidence into 3/3 and awards XP, a skill level and achievement once", () => {
    const initial = createDemoState();
    const result = demoReducer(initial, {
      type: "set-quest-evidence",
      questId: "quest-lead-pilot",
      evidenceId: "proof-pilot-demo",
      completed: true,
      completedAt: "2026-09-23",
    });
    expect(result.quests.find((item) => item.id === "quest-lead-pilot")).toMatchObject({
      status: "completed",
      progressPercent: 100,
    });
    expect(result.user.totalXp).toBe(initial.user.totalXp + 600);
    expect(result.skills.find((item) => item.id === "skill-project-management")?.currentLevel).toBe(4);
    expect(result.achievements.filter((item) => item.id === "achievement-quest-lead-pilot")).toHaveLength(1);
    expect(
      demoReducer(result, {
        type: "set-quest-evidence",
        questId: "quest-lead-pilot",
        evidenceId: "proof-pilot-demo",
        completed: true,
      }),
    ).toBe(result);
  });

  it("keeps unknown evidence unchanged and supports profile, team and AI updates", () => {
    let state = createDemoState();
    expect(
      demoReducer(state, {
        type: "set-quest-evidence",
        questId: "quest-lead-pilot",
        evidenceId: "unknown",
        completed: true,
      }),
    ).toBe(state);
    state = demoReducer(state, {
      type: "set-goal",
      goal: { ...state.goal, role: "Product Owner" },
    });
    state = demoReducer(state, {
      type: "set-visibility",
      visibility: { profile: "private", skills: "team", achievements: "company" },
    });
    state = demoReducer(state, { type: "set-team-role", role: "  Lead analyst  " });
    const message = {
      id: "message-test",
      role: "user" as const,
      content: "Что делать дальше?",
      createdAt: "2026-09-23T10:00:00+05:00",
    };
    state = demoReducer(state, { type: "append-ai-message", message });
    const deduplicated = demoReducer(state, { type: "append-ai-message", message });
    state = demoReducer(deduplicated, {
      type: "rate-ai-message",
      messageId: "message-test",
      feedback: "like",
    });
    expect(state.goal.role).toBe("Product Owner");
    expect(state.user.visibility.profile).toBe("private");
    expect(state.teamMission.role).toBe("Lead analyst");
    expect(state.aiMessages.filter((item) => item.id === message.id)).toHaveLength(1);
    expect(state.aiMessages.at(-1)?.feedback).toBe("like");
  });
});

describe("versioned persistence", () => {
  it("serializes only the permitted local demo state and merges it onto fresh fixtures", () => {
    const state = createDemoState();
    const persisted = toPersistedDemoState(state);
    expect(persisted.version).toBe(DEMO_STATE_VERSION);
    expect(persisted).not.toHaveProperty("quests");
    const changed = {
      ...persisted,
      savedCourseIds: ["learning-project-leadership", "learning-project-leadership"],
      appliedOpportunityIds: ["opportunity-pm-vacancy"],
      visibility: { ...persisted.visibility, profile: "private" as const },
    };
    const parsed = parsePersistedDemoState(changed);
    expect(parsed?.savedCourseIds).toEqual(["learning-project-leadership"]);
    const merged = mergePersistedDemoState(state, parsed!);
    expect(merged.learning.find((item) => item.id === "learning-project-leadership")?.saved).toBe(true);
    expect(merged.opportunities.find((item) => item.id === "opportunity-pm-vacancy")?.applied).toBe(true);
    expect(merged.user.visibility.profile).toBe("private");
  });

  it("rejects incompatible or malformed persisted values", () => {
    expect(parsePersistedDemoState(null)).toBeNull();
    expect(parsePersistedDemoState({ version: 99 })).toBeNull();
    expect(parsePersistedDemoState({ version: DEMO_STATE_VERSION })).toBeNull();
    const valid = toPersistedDemoState(createDemoState());
    expect(parsePersistedDemoState({ ...valid, savedCourseIds: [1] })).toBeNull();
    expect(parsePersistedDemoState({ ...valid, selectedTabs: { ...valid.selectedTabs, quests: "bad" } })).toBeNull();
    expect(parsePersistedDemoState({ ...valid, aiMessages: [{ bad: true }] })).toBeNull();
  });

  it("loads, saves, clears and safely resets corrupted storage", () => {
    const storage = memoryStorage();
    const state = createDemoState();
    expect(saveDemoState(state, storage)).toBe(true);
    expect(loadDemoState(createDemoState(), storage).user.fullName).toBe("Анна Смирнова");
    expect(clearPersistedDemoState(storage)).toBe(true);
    expect(storage.getItem(DEMO_STORAGE_KEY)).toBeNull();
    storage.setItem(DEMO_STORAGE_KEY, "not json");
    expect(loadDemoState(state, storage)).toBe(state);
    storage.setItem(DEMO_STORAGE_KEY, JSON.stringify({ version: 77 }));
    expect(loadDemoState(state, storage)).toBe(state);
    expect(storage.getItem(DEMO_STORAGE_KEY)).toBeNull();
  });

  it("absorbs unavailable or throwing storage without breaking SSR", () => {
    const state = createDemoState();
    const throwing: StorageLike = {
      getItem: () => { throw new Error("denied"); },
      setItem: () => { throw new Error("denied"); },
      removeItem: () => { throw new Error("denied"); },
    };
    expect(loadDemoState(state, null)).toBe(state);
    expect(loadDemoState(state, throwing)).toBe(state);
    expect(saveDemoState(state, null)).toBe(false);
    expect(saveDemoState(state, throwing)).toBe(false);
    expect(clearPersistedDemoState(null)).toBe(false);
    expect(clearPersistedDemoState(throwing)).toBe(false);
  });
});

describe("framework-independent store", () => {
  it("dispatches, publishes, unsubscribes and resets", () => {
    const listener = vi.fn();
    const store = createDemoStore({ persist: false });
    const unsubscribe = store.subscribe(listener);
    const initial = store.getState();
    store.dispatch({ type: "toggle-course-saved", learningId: "learning-project-leadership" });
    expect(listener).toHaveBeenCalledOnce();
    expect(store.getState()).not.toBe(initial);
    unsubscribe();
    store.reset();
    expect(listener).toHaveBeenCalledOnce();
  });

  it("hydrates and persists through an injected storage adapter", () => {
    const storage = memoryStorage();
    const seeded = createDemoState();
    const persisted = toPersistedDemoState(seeded);
    persisted.savedResourceIds = ["resource-pm-book"];
    storage.setItem(DEMO_STORAGE_KEY, JSON.stringify(persisted));
    const store = createDemoStore({ storage });
    expect(store.getState().library.find((item) => item.id === "resource-pm-book")?.saved).toBe(true);
    store.dispatch({ type: "set-tab", section: "library", value: "saved" });
    expect(storage.getItem(DEMO_STORAGE_KEY)).toContain('"library":"saved"');
  });
});
