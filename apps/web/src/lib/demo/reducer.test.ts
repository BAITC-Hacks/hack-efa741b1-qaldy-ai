import { describe, expect, it, vi } from "vitest";
import { createDemoState } from "./fixtures";
import { toPersistedDemoState } from "./persistence";
import { demoReducer, type DemoAction } from "./reducer";
import { createDemoStore } from "./store";
import type { StorageLike } from "./types";

describe("demoReducer", () => {
  it("replaces state and updates simple preference actions", () => {
    let state = createDemoState();
    const replacement = { ...state, asOfDate: "2026-09-23" as const };
    expect(demoReducer(state, { type: "replace-state", state: replacement })).toBe(replacement);

    state = demoReducer(state, { type: "toggle-course-saved", learningId: "learning-project-leadership" });
    expect(state.learning.find((item) => item.id === "learning-project-leadership")?.saved).toBe(true);
    state = demoReducer(state, { type: "toggle-opportunity-saved", opportunityId: "opportunity-pm-vacancy" });
    expect(state.opportunities.find((item) => item.id === "opportunity-pm-vacancy")?.saved).toBe(true);
    state = demoReducer(state, { type: "apply-to-opportunity", opportunityId: "opportunity-pm-vacancy" });
    expect(state.opportunities.find((item) => item.id === "opportunity-pm-vacancy")?.applied).toBe(true);
    state = demoReducer(state, { type: "toggle-resource-saved", resourceId: "resource-pm-book" });
    expect(state.library.find((item) => item.id === "resource-pm-book")?.saved).toBe(true);
    state = demoReducer(state, {
      type: "mark-resource-viewed",
      resourceId: "resource-pm-book",
      viewedAt: "2026-09-23T12:00:00+05:00",
    });
    expect(state.library.find((item) => item.id === "resource-pm-book")?.lastViewedAt).toContain("12:00");
  });

  it("clamps course progress and never regresses a completed course", () => {
    const base = createDemoState();
    const started = demoReducer(base, {
      type: "set-course-progress",
      learningId: "learning-project-leadership",
      progressPercent: 45.6,
    });
    expect(started.learning.find((item) => item.id === "learning-project-leadership")).toMatchObject({
      status: "in_progress",
      progressPercent: 46,
    });
    const reset = demoReducer(started, {
      type: "set-course-progress",
      learningId: "learning-project-leadership",
      progressPercent: -5,
    });
    expect(reset.learning.find((item) => item.id === "learning-project-leadership")).toMatchObject({
      status: "recommended",
      progressPercent: 0,
    });
    const unchanged = demoReducer(base, {
      type: "set-course-progress",
      learningId: "learning-presentations",
      progressPercent: 20,
    });
    expect(unchanged.learning.find((item) => item.id === "learning-presentations")?.progressPercent).toBe(100);
  });

  it("completes a course and creates at most one certificate", () => {
    const base = createDemoState();
    const missing = demoReducer(base, { type: "complete-course", learningId: "missing" });
    expect(missing).toBe(base);
    const completed = demoReducer(base, {
      type: "complete-course",
      learningId: "learning-project-leadership",
      completedAt: "bad-date",
    });
    expect(completed.learning.find((item) => item.id === "learning-project-leadership")).toMatchObject({
      status: "completed",
      progressPercent: 100,
    });
    expect(completed.certificates.filter((item) => item.sourceLearningId === "learning-project-leadership")).toHaveLength(1);
    const replayed = demoReducer(completed, {
      type: "complete-course",
      learningId: "learning-project-leadership",
      completedAt: "2026-09-24",
    });
    expect(replayed.certificates.filter((item) => item.sourceLearningId === "learning-project-leadership")).toHaveLength(1);
  });

  it("starts only available quests", () => {
    const base = createDemoState();
    const started = demoReducer(base, { type: "start-quest", questId: "quest-strategy-case" });
    expect(started.quests.find((item) => item.id === "quest-strategy-case")?.status).toBe("active");
    const active = base.quests.find((item) => item.id === "quest-lead-pilot");
    expect(demoReducer(base, { type: "start-quest", questId: active?.id ?? "" }).quests.find((item) => item.id === active?.id)?.status).toBe("active");
  });

  it("updates weighted quest evidence and applies completion effects once", () => {
    const base = createDemoState();
    const target = base.quests.find((item) => item.id === "quest-lead-pilot")!;
    const incomplete = target.evidence.find((item) => !item.completed)!;
    const partial = demoReducer(base, {
      type: "set-quest-evidence",
      questId: target.id,
      evidenceId: target.evidence[0].id,
      completed: false,
    });
    expect(partial.quests.find((item) => item.id === target.id)?.progressPercent).toBeLessThan(60);

    const completed = demoReducer(base, {
      type: "set-quest-evidence",
      questId: target.id,
      evidenceId: incomplete.id,
      completed: true,
      completedAt: "2026-09-23T19:00:00+05:00",
    });
    expect(completed.quests.find((item) => item.id === target.id)).toMatchObject({ status: "completed", progressPercent: 100 });
    expect(completed.user.totalXp).toBe(base.user.totalXp + target.xpReward);
    expect(completed.achievements.some((item) => item.id === `achievement-${target.id}`)).toBe(true);
    if (target.skillGain) {
      const before = base.skills.find((item) => item.id === target.skillGain?.skillId)!;
      const after = completed.skills.find((item) => item.id === target.skillGain?.skillId)!;
      expect(after.currentLevel).toBe(Math.min(before.maxLevel, before.currentLevel + target.skillGain.levels));
    }

    expect(
      demoReducer(completed, {
        type: "set-quest-evidence",
        questId: target.id,
        evidenceId: incomplete.id,
        completed: true,
      }),
    ).toBe(completed);
    expect(
      demoReducer(base, {
        type: "set-quest-evidence",
        questId: "missing",
        evidenceId: "missing",
        completed: true,
      }),
    ).toBe(base);
    expect(
      demoReducer(base, {
        type: "set-quest-evidence",
        questId: target.id,
        evidenceId: "missing",
        completed: true,
      }),
    ).toBe(base);
  });

  it("deduplicates AI messages and updates profile-related state", () => {
    let state = createDemoState();
    const existing = state.aiMessages[0];
    expect(demoReducer(state, { type: "append-ai-message", message: existing })).toBe(state);
    const message = { ...existing, id: "new-message", content: "Новый вопрос" };
    state = demoReducer(state, { type: "append-ai-message", message });
    expect(state.aiMessages.at(-1)?.id).toBe("new-message");
    state = demoReducer(state, { type: "rate-ai-message", messageId: "new-message", feedback: "like" });
    expect(state.aiMessages.at(-1)?.feedback).toBe("like");
    state = demoReducer(state, { type: "set-goal", goal: { ...state.goal, role: "Product Owner" } });
    expect(state.goal.role).toBe("Product Owner");
    state = demoReducer(state, {
      type: "set-visibility",
      visibility: { profile: "private", skills: "company", achievements: "team" },
    });
    expect(state.user.visibility.profile).toBe("private");
    state = demoReducer(state, { type: "set-team-role", role: "  Фасилитатор  " });
    expect(state.teamMission.role).toBe("Фасилитатор");
  });

  it.each([
    ["quests", "active"],
    ["learning", "saved"],
    ["opportunities", "rotation"],
    ["library", "recent"],
  ] as const)("sets the %s tab", (section, value) => {
    const state = demoReducer(createDemoState(), { type: "set-tab", section, value } as DemoAction);
    expect(state.selectedTabs[section]).toBe(value);
  });
});

describe("createDemoStore", () => {
  it("publishes changed actions, skips no-ops, persists and unsubscribes", () => {
    const data = new Map<string, string>();
    const storage: StorageLike = {
      getItem: (key) => data.get(key) ?? null,
      setItem: (key, value) => void data.set(key, value),
      removeItem: (key) => void data.delete(key),
    };
    const store = createDemoStore({ storage });
    const listener = vi.fn();
    const unsubscribe = store.subscribe(listener);
    const existing = store.getState().aiMessages[0];
    expect(store.dispatch({ type: "append-ai-message", message: existing })).toBe(store.getState());
    expect(listener).not.toHaveBeenCalled();

    store.dispatch({ type: "toggle-course-saved", learningId: "learning-project-leadership" });
    expect(listener).toHaveBeenCalledOnce();
    expect(data.size).toBe(1);
    expect(toPersistedDemoState(store.getState()).savedCourseIds).toContain("learning-project-leadership");
    unsubscribe();
    store.reset();
    expect(listener).toHaveBeenCalledOnce();
  });

  it("can run as an isolated non-persistent store", () => {
    const initialState = createDemoState();
    const store = createDemoStore({ initialState, storage: null, persist: false });
    expect(store.getState()).toBe(initialState);
    expect(store.reset()).not.toBe(initialState);
  });
});
