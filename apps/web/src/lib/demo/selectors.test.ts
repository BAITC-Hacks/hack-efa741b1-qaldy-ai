import { describe, expect, it } from "vitest";
import { createDemoState } from "./fixtures";
import {
  calculateNonAdditiveImpact,
  calculateProjectedReadiness,
  calculateQuestProgress,
  calculateReadiness,
  calculateXpProgress,
  clamp,
  filterLearning,
  filterLibrary,
  filterOpportunities,
  filterQuests,
  formatDateRu,
  formatDuration,
  getQuestDisplayStatus,
  isOverdue,
  matchesSearch,
  normalizeSearch,
  searchByText,
  selectDashboardStats,
  selectPrimaryQuest,
  selectReadiness,
  selectRecommendedOpportunity,
  selectSkillGaps,
} from "./selectors";
import type { Quest, Skill } from "./types";

const skill = (overrides: Partial<Skill> = {}): Skill => ({
  id: "skill",
  name: "Лидерство",
  category: "leadership",
  currentLevel: 2,
  targetLevel: 4,
  maxLevel: 5,
  readinessWeight: 1,
  status: "developing",
  relatedSkillIds: [],
  evidence: [],
  ...overrides,
});

const quest = (overrides: Partial<Quest> = {}): Quest => ({
  id: "quest",
  title: "Пилотный проект",
  description: "Провести защиту",
  kind: "career",
  difficulty: "hard",
  status: "active",
  dueDate: "2026-09-22",
  xpReward: 100,
  skillIds: ["skill"],
  progressPercent: 60,
  evidence: [],
  isPrimary: true,
  ...overrides,
});

describe("numeric selectors", () => {
  it("clamps finite and invalid values", () => {
    expect(clamp(-1)).toBe(0);
    expect(clamp(101)).toBe(100);
    expect(clamp(7, 5, 9)).toBe(7);
    expect(clamp(Number.NaN, 5, 9)).toBe(5);
    expect(clamp(Number.POSITIVE_INFINITY, 5, 9)).toBe(5);
  });

  it("calculates XP at zero, before and exactly on a level boundary", () => {
    expect(calculateXpProgress(-10)).toMatchObject({ level: 1, currentLevelXp: 0, percentage: 0 });
    expect(calculateXpProgress(999)).toMatchObject({ level: 1, currentLevelXp: 999, percentage: 100 });
    expect(calculateXpProgress(1_000)).toMatchObject({
      level: 2,
      currentLevelXp: 0,
      nextLevelXp: 2_000,
      percentage: 0,
    });
    expect(calculateXpProgress(Number.NaN, 0).totalXp).toBe(0);
  });

  it("keeps weighted readiness in the 0–100 range", () => {
    expect(calculateReadiness([])).toBe(0);
    expect(calculateReadiness([skill({ currentLevel: -2 })])).toBe(0);
    expect(calculateReadiness([skill({ currentLevel: 9 })])).toBe(100);
    expect(
      calculateReadiness([
        skill({ id: "a", currentLevel: 2, targetLevel: 4, readinessWeight: 1 }),
        skill({ id: "b", currentLevel: 4, targetLevel: 4, readinessWeight: 3 }),
        skill({ id: "ignored", readinessWeight: -1 }),
      ]),
    ).toBe(88);
  });

  it("sorts positive skill gaps by weighted impact", () => {
    const gaps = selectSkillGaps([
      skill({ id: "small", name: "Аналитика", currentLevel: 3, targetLevel: 4, readinessWeight: 1 }),
      skill({ id: "large", name: "Лидерство", currentLevel: 1, targetLevel: 4, readinessWeight: 2 }),
      skill({ id: "done", currentLevel: 5, targetLevel: 4 }),
    ]);
    expect(gaps.map((item) => item.skillId)).toEqual(["large", "small"]);
    expect(gaps[0]).toMatchObject({ gap: 3, weightedGap: 6 });
  });

  it("uses evidence weights instead of assuming that two of three is 66.7%", () => {
    expect(calculateQuestProgress([])).toBe(0);
    expect(
      calculateQuestProgress([
        { id: "a", label: "A", completed: true, weight: 30 },
        { id: "b", label: "B", completed: true, weight: 30 },
        { id: "c", label: "C", completed: false, weight: 40 },
      ]),
    ).toBe(60);
    expect(
      calculateQuestProgress([
        { id: "a", label: "A", completed: true, weight: 0 },
        { id: "b", label: "B", completed: false, weight: -2 },
      ]),
    ).toBe(50);
  });

  it("combines overlapping impacts non-additively and respects caps", () => {
    expect(calculateNonAdditiveImpact([])).toBe(0);
    expect(calculateNonAdditiveImpact([10, 10])).toBe(19);
    expect(calculateNonAdditiveImpact([80, 80], 20)).toBe(20);
    expect(calculateProjectedReadiness(95, [20])).toBe(100);
  });
});

describe("dates and status", () => {
  it("detects overdue only for a valid earlier calendar date", () => {
    expect(isOverdue(undefined, "2026-09-23")).toBe(false);
    expect(isOverdue("invalid", "2026-09-23")).toBe(false);
    expect(isOverdue("2026-09-22T23:59:00-05:00", "2026-09-23")).toBe(true);
    expect(isOverdue("2026-09-23", "2026-09-23")).toBe(false);
    expect(getQuestDisplayStatus(quest(), "2026-09-23")).toBe("overdue");
    expect(getQuestDisplayStatus(quest({ status: "completed" }), "2026-09-23")).toBe("completed");
  });

  it("formats dates and durations with deterministic Russian output", () => {
    expect(formatDateRu("not-a-date")).toBe("—");
    expect(formatDateRu("2026-09-23")).toContain("23");
    expect(formatDateRu("2026-09-23", { month: "long" })).toContain("сентябр");
    expect(formatDuration(Number.NaN)).toBe("0 мин");
    expect(formatDuration(45)).toBe("45 мин");
    expect(formatDuration(120)).toBe("2 ч");
    expect(formatDuration(135)).toBe("2 ч 15 мин");
  });
});

describe("search and filters", () => {
  it("normalizes accents, punctuation, case and Russian ё", () => {
    expect(normalizeSearch("  Ёлка—CAFÉ! ")).toBe("елка cafe");
    expect(matchesSearch(undefined, ["Любое значение"])).toBe(true);
    expect(matchesSearch("ЛИД проект", ["Лидерство", "Пилотный проект"])).toBe(true);
    expect(matchesSearch("финансы", ["Лидерство"])).toBe(false);
    expect(searchByText([{ label: "Alpha" }, { label: "Beta" }], "bet", (item) => [item.label])).toEqual([
      { label: "Beta" },
    ]);
  });

  it("combines quest tabs, overdue, type, difficulty, skill and text", () => {
    const state = createDemoState();
    const result = filterQuests(
      state.quests,
      {
        tab: "active",
        overdueOnly: true,
        kind: "practice",
        difficulty: "easy",
        skillId: "skill-communication",
        query: "feedback коммуникация",
      },
      state.asOfDate,
      state.skills,
    );
    expect(result.map((item) => item.id)).toEqual(["quest-stakeholder-feedback"]);
    expect(filterQuests(state.quests, { tab: "all" }, state.asOfDate)).toHaveLength(state.quests.length);
  });

  it("filters learning by saved/status, format, skill and duration", () => {
    const state = createDemoState();
    expect(filterLearning(state.learning, { tab: "saved" })).toEqual(
      expect.arrayContaining(state.learning.filter((item) => item.saved)),
    );
    const result = filterLearning(
      state.learning,
      {
        tab: "in_progress",
        format: "course",
        skillId: "skill-strategy",
        maxDurationMinutes: 400,
        query: "стратегическое",
      },
      state.skills,
    );
    expect(result.map((item) => item.id)).toEqual(["learning-strategic-thinking"]);
  });

  it("filters opportunities and keeps best matches first", () => {
    const state = createDemoState();
    const all = filterOpportunities(state.opportunities, { minimumMatch: 0 });
    expect(all[0].matchPercent).toBeGreaterThanOrEqual(all.at(-1)?.matchPercent ?? 0);
    expect(
      filterOpportunities(
        state.opportunities,
        {
          kind: "project",
          location: "Алматы",
          savedOnly: true,
          appliedOnly: false,
          minimumMatch: 70,
          query: "ассистент проект",
        },
        state.skills,
      ).map((item) => item.id),
    ).toEqual(["opportunity-pm-assistant"]);
  });

  it("filters library and sorts recent resources newest first", () => {
    const state = createDemoState();
    const recent = filterLibrary(state.library, { recentOnly: true }, state.skills);
    expect(recent.map((item) => item.id)).toEqual([
      "resource-project-charter",
      "resource-strategy-article",
      "resource-feedback-video",
    ]);
    expect(
      filterLibrary(
        state.library,
        {
          kind: "template",
          tag: "проект",
          savedOnly: true,
          skillId: "skill-project-management",
          query: "чартер",
        },
        state.skills,
      ).map((item) => item.id),
    ).toEqual(["resource-project-charter"]);
  });
});

describe("aggregate selectors", () => {
  it("derives dashboard values from one shared state", () => {
    const state = createDemoState();
    const stats = selectDashboardStats(state);
    expect(stats.readiness).toBe(selectReadiness(state));
    expect(stats.activeQuests).toBeGreaterThan(0);
    expect(stats.overdueQuests).toBe(1);
    expect(stats.savedCourses).toBe(state.learning.filter((item) => item.saved).length);
    expect(stats.xp.totalXp).toBe(state.user.totalXp);
    expect(selectPrimaryQuest(state)?.isPrimary).toBe(true);
  });

  it("selects the highest-match opportunity not yet applied to", () => {
    const state = createDemoState();
    const expected = [...state.opportunities]
      .filter((item) => !item.applied)
      .sort((a, b) => b.matchPercent - a.matchPercent)[0];
    expect(selectRecommendedOpportunity(state)?.id).toBe(expected.id);
    expect(
      selectRecommendedOpportunity({
        ...state,
        opportunities: state.opportunities.map((item) => ({ ...item, applied: true })),
      }),
    ).toBeUndefined();
  });
});
