import { describe, expect, it, vi } from "vitest";
import { createDemoState } from "./fixtures";
import {
  clearPersistedDemoState,
  DEMO_STORAGE_KEY,
  getBrowserStorage,
  loadDemoState,
  mergePersistedDemoState,
  parsePersistedDemoState,
  saveDemoState,
  toPersistedDemoState,
} from "./persistence";
import type { PersistedDemoStateV1, StorageLike } from "./types";

function memoryStorage(initial: Record<string, string> = {}): StorageLike & { data: Map<string, string> } {
  const data = new Map(Object.entries(initial));
  return {
    data,
    getItem: (key) => data.get(key) ?? null,
    setItem: (key, value) => void data.set(key, value),
    removeItem: (key) => void data.delete(key),
  };
}

function validPersisted(): PersistedDemoStateV1 {
  return toPersistedDemoState(createDemoState());
}

describe("demo persistence parser", () => {
  it("round-trips the safe subset and removes duplicate ids", () => {
    const source = validPersisted();
    const parsed = parsePersistedDemoState({
      ...source,
      savedCourseIds: ["one", "one", "two"],
      aiMessages: Array.from({ length: 105 }, (_, index) => ({
        id: `message-${index}`,
        role: index % 2 ? "user" : "assistant",
        content: `message ${index}`,
        createdAt: "2026-09-23T10:00:00+05:00",
        feedback: index === 104 ? "like" : "unsupported",
      })),
    });

    expect(parsed?.savedCourseIds).toEqual(["one", "two"]);
    expect(parsed?.aiMessages).toHaveLength(100);
    expect(parsed?.aiMessages.at(-1)?.feedback).toBe("like");
    expect(parsed?.aiMessages[0]).not.toHaveProperty("feedback");
  });

  it.each([
    null,
    [],
    { version: 99 },
    { ...validPersisted(), selectedTabs: null },
    { ...validPersisted(), selectedTabs: { ...validPersisted().selectedTabs, quests: "wrong" } },
    { ...validPersisted(), selectedTabs: { ...validPersisted().selectedTabs, learning: "wrong" } },
    { ...validPersisted(), selectedTabs: { ...validPersisted().selectedTabs, opportunities: "wrong" } },
    { ...validPersisted(), selectedTabs: { ...validPersisted().selectedTabs, library: "wrong" } },
    { ...validPersisted(), visibility: null },
    { ...validPersisted(), visibility: { profile: "wrong", skills: "team", achievements: "team" } },
    { ...validPersisted(), savedCourseIds: [1] },
    { ...validPersisted(), savedOpportunityIds: null },
    { ...validPersisted(), appliedOpportunityIds: "x" },
    { ...validPersisted(), savedResourceIds: {} },
    { ...validPersisted(), aiMessages: null },
    { ...validPersisted(), aiMessages: [{ role: "assistant" }] },
    {
      ...validPersisted(),
      aiMessages: [{ id: "x", role: "other", content: "x", createdAt: "2026" }],
    },
    {
      ...validPersisted(),
      aiMessages: [{ id: "x".repeat(161), role: "user", content: "x", createdAt: "2026" }],
    },
  ])("rejects malformed or incompatible payload %#", (payload) => {
    expect(parsePersistedDemoState(payload)).toBeNull();
  });

  it("merges only persisted fields into fresh fixture data", () => {
    const base = createDemoState();
    const persisted: PersistedDemoStateV1 = {
      ...validPersisted(),
      savedCourseIds: ["learning-project-leadership"],
      savedOpportunityIds: ["opportunity-pm-vacancy"],
      appliedOpportunityIds: ["opportunity-pm-vacancy"],
      savedResourceIds: ["resource-pm-book"],
      visibility: { profile: "private", skills: "company", achievements: "team" },
      aiMessages: [],
    };
    const merged = mergePersistedDemoState(base, persisted);

    expect(merged.goal).toEqual(base.goal);
    expect(merged.learning.find((item) => item.id === "learning-project-leadership")?.saved).toBe(true);
    expect(merged.learning.find((item) => item.id === "learning-strategic-thinking")?.saved).toBe(false);
    expect(merged.opportunities.find((item) => item.id === "opportunity-pm-vacancy")).toMatchObject({
      saved: true,
      applied: true,
    });
    expect(merged.library.find((item) => item.id === "resource-pm-book")?.saved).toBe(true);
    expect(merged.user.visibility.profile).toBe("private");
  });
});

describe("storage operations", () => {
  it("loads valid state and removes incompatible persisted data", () => {
    const base = createDemoState();
    const valid = validPersisted();
    const storage = memoryStorage({ [DEMO_STORAGE_KEY]: JSON.stringify(valid) });
    expect(loadDemoState(base, storage).selectedTabs).toEqual(valid.selectedTabs);

    storage.data.set(DEMO_STORAGE_KEY, JSON.stringify({ version: 999 }));
    expect(loadDemoState(base, storage)).toBe(base);
    expect(storage.data.has(DEMO_STORAGE_KEY)).toBe(false);
  });

  it("returns the fixture for empty, unavailable or broken storage", () => {
    const base = createDemoState();
    expect(loadDemoState(base, null)).toBe(base);
    expect(loadDemoState(base, memoryStorage())).toBe(base);
    const malformed = memoryStorage({ [DEMO_STORAGE_KEY]: "{" });
    expect(loadDemoState(base, malformed)).toBe(base);
    expect(
      loadDemoState(base, {
        getItem: () => {
          throw new Error("blocked");
        },
        setItem: vi.fn(),
        removeItem: vi.fn(),
      }),
    ).toBe(base);
  });

  it("saves and clears state, reporting storage failures", () => {
    const storage = memoryStorage();
    const state = createDemoState();
    expect(saveDemoState(state, null)).toBe(false);
    expect(saveDemoState(state, storage)).toBe(true);
    expect(JSON.parse(storage.data.get(DEMO_STORAGE_KEY) ?? "{}").version).toBe(1);
    expect(clearPersistedDemoState(storage)).toBe(true);
    expect(storage.data.has(DEMO_STORAGE_KEY)).toBe(false);
    expect(clearPersistedDemoState(null)).toBe(false);

    const broken: StorageLike = {
      getItem: vi.fn(),
      setItem: () => {
        throw new Error("quota");
      },
      removeItem: () => {
        throw new Error("blocked");
      },
    };
    expect(saveDemoState(state, broken)).toBe(false);
    expect(clearPersistedDemoState(broken)).toBe(false);
  });

  it("uses browser localStorage when available", () => {
    expect(getBrowserStorage()).toBe(window.localStorage);
  });
});
