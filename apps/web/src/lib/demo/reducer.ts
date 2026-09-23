import { calculateQuestProgress, calculateXpProgress, clamp } from "./selectors";
import type {
  AiMessage,
  CareerGoal,
  DemoState,
  DemoTabs,
  VisibilitySettings,
} from "./types";

type SetTabAction =
  | { type: "set-tab"; section: "quests"; value: DemoTabs["quests"] }
  | { type: "set-tab"; section: "learning"; value: DemoTabs["learning"] }
  | { type: "set-tab"; section: "opportunities"; value: DemoTabs["opportunities"] }
  | { type: "set-tab"; section: "library"; value: DemoTabs["library"] };

export type DemoAction =
  | { type: "replace-state"; state: DemoState }
  | { type: "toggle-course-saved"; learningId: string }
  | { type: "set-course-progress"; learningId: string; progressPercent: number }
  | { type: "complete-course"; learningId: string; completedAt?: string }
  | { type: "toggle-opportunity-saved"; opportunityId: string }
  | { type: "apply-to-opportunity"; opportunityId: string }
  | { type: "toggle-resource-saved"; resourceId: string }
  | { type: "mark-resource-viewed"; resourceId: string; viewedAt: string }
  | { type: "start-quest"; questId: string }
  | {
      type: "set-quest-evidence";
      questId: string;
      evidenceId: string;
      completed: boolean;
      completedAt?: string;
    }
  | { type: "append-ai-message"; message: AiMessage }
  | { type: "rate-ai-message"; messageId: string; feedback: "like" | "dislike" }
  | { type: "set-goal"; goal: CareerGoal }
  | { type: "set-visibility"; visibility: VisibilitySettings }
  | { type: "set-team-role"; role: string }
  | SetTabAction;

function isoDatePart(value: string | undefined, fallback: string): `${number}-${number}-${number}` {
  const candidate = value?.slice(0, 10) ?? fallback.slice(0, 10);
  return /^\d{4}-\d{2}-\d{2}$/.test(candidate)
    ? (candidate as `${number}-${number}-${number}`)
    : (fallback.slice(0, 10) as `${number}-${number}-${number}`);
}

export function demoReducer(state: DemoState, action: DemoAction): DemoState {
  switch (action.type) {
    case "replace-state":
      return action.state;

    case "toggle-course-saved":
      return {
        ...state,
        learning: state.learning.map((item) =>
          item.id === action.learningId ? { ...item, saved: !item.saved } : item,
        ),
      };

    case "set-course-progress": {
      const progress = clamp(Math.round(action.progressPercent));
      return {
        ...state,
        learning: state.learning.map((item) =>
          item.id === action.learningId && item.status !== "completed"
            ? {
                ...item,
                progressPercent: progress,
                status: progress > 0 ? "in_progress" : "recommended",
              }
            : item,
        ),
      };
    }

    case "complete-course": {
      const learning = state.learning.find((item) => item.id === action.learningId);
      if (!learning) return state;
      const alreadyCertified = state.certificates.some(
        (certificate) => certificate.sourceLearningId === learning.id,
      );
      return {
        ...state,
        learning: state.learning.map((item) =>
          item.id === learning.id
            ? { ...item, status: "completed", progressPercent: 100 }
            : item,
        ),
        certificates: alreadyCertified
          ? state.certificates
          : [
              ...state.certificates,
              {
                id: `certificate-${learning.id}`,
                sourceLearningId: learning.id,
                title: learning.title,
                issuer: learning.provider,
                issuedAt: isoDatePart(action.completedAt, state.asOfDate),
              },
            ],
      };
    }

    case "toggle-opportunity-saved":
      return {
        ...state,
        opportunities: state.opportunities.map((item) =>
          item.id === action.opportunityId ? { ...item, saved: !item.saved } : item,
        ),
      };

    case "apply-to-opportunity":
      return {
        ...state,
        opportunities: state.opportunities.map((item) =>
          item.id === action.opportunityId ? { ...item, applied: true } : item,
        ),
      };

    case "toggle-resource-saved":
      return {
        ...state,
        library: state.library.map((item) =>
          item.id === action.resourceId ? { ...item, saved: !item.saved } : item,
        ),
      };

    case "mark-resource-viewed":
      return {
        ...state,
        library: state.library.map((item) =>
          item.id === action.resourceId ? { ...item, lastViewedAt: action.viewedAt } : item,
        ),
      };

    case "start-quest":
      return {
        ...state,
        quests: state.quests.map((quest) =>
          quest.id === action.questId && quest.status === "available"
            ? { ...quest, status: "active" }
            : quest,
        ),
      };

    case "set-quest-evidence": {
      const quest = state.quests.find((item) => item.id === action.questId);
      if (!quest || quest.status === "completed" || quest.status === "locked") return state;
      const evidence = quest.evidence.map((item) =>
        item.id === action.evidenceId
          ? {
              ...item,
              completed: action.completed,
              completedAt: action.completed
                ? isoDatePart(action.completedAt, state.asOfDate)
                : undefined,
            }
          : item,
      );
      const progressPercent = calculateQuestProgress(evidence);
      const hasEvidence = evidence.some((item) => item.id === action.evidenceId);
      if (!hasEvidence) return state;
      const justCompleted = progressPercent === 100;
      const updatedQuest = {
        ...quest,
        evidence,
        progressPercent,
        status: justCompleted ? ("completed" as const) : ("active" as const),
      };
      const existingAchievement = state.achievements.some(
        (achievement) => achievement.id === `achievement-${quest.id}`,
      );
      const skillGain = justCompleted ? quest.skillGain : undefined;
      const totalXp = justCompleted ? state.user.totalXp + quest.xpReward : state.user.totalXp;

      return {
        ...state,
        user: justCompleted
          ? { ...state.user, totalXp, level: calculateXpProgress(totalXp).level }
          : state.user,
        quests: state.quests.map((item) => (item.id === quest.id ? updatedQuest : item)),
        skills: skillGain
          ? state.skills.map((skill) =>
              skill.id === skillGain.skillId
                ? {
                    ...skill,
                    currentLevel: Math.min(skill.maxLevel, skill.currentLevel + skillGain.levels),
                  }
                : skill,
            )
          : state.skills,
        achievements:
          justCompleted && !existingAchievement
            ? [
                ...state.achievements,
                {
                  id: `achievement-${quest.id}`,
                  title: `Квест «${quest.title}» завершён`,
                  description: "Все доказательства приняты",
                  earnedAt: isoDatePart(action.completedAt, state.asOfDate),
                  icon: "target",
                  xpAwarded: quest.xpReward,
                },
              ]
            : state.achievements,
      };
    }

    case "append-ai-message":
      return state.aiMessages.some((message) => message.id === action.message.id)
        ? state
        : { ...state, aiMessages: [...state.aiMessages, action.message] };

    case "rate-ai-message":
      return {
        ...state,
        aiMessages: state.aiMessages.map((message) =>
          message.id === action.messageId ? { ...message, feedback: action.feedback } : message,
        ),
      };

    case "set-goal":
      return { ...state, goal: action.goal };

    case "set-visibility":
      return { ...state, user: { ...state.user, visibility: action.visibility } };

    case "set-team-role":
      return { ...state, teamMission: { ...state.teamMission, role: action.role.trim() } };

    case "set-tab":
      return {
        ...state,
        selectedTabs: { ...state.selectedTabs, [action.section]: action.value },
      } as DemoState;
  }
}
