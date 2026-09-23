"use client";

import { useEffect, useMemo, useState } from "react";

import { completeActivity, fetchEmployeeJourney, fetchEmployees } from "./api";
import type { EmployeeJourney, EmployeeListItem, SkillChange } from "./types";
import { useI18n } from "@/lib/i18n";
import { AUTH_CHANGE_EVENT, fetchAuthIdentity, type AuthIdentity } from "@/lib/auth";

const emptyReasonLabels: Record<string, string> = {
  no_target: "Сначала задайте карьерную цель.",
  catalog_gap: "Для актуального разрыва пока нет активности в каталоге.",
  prerequisite_blocked: "Доступные шаги требуют предварительных навыков.",
  already_completed: "Подходящие активности уже завершены.",
  already_in_progress: "Подходящий шаг уже находится в работе.",
  no_future_session: "Для подходящих активностей пока нет будущей сессии.",
  no_gap: "Требования целевого профиля уже выполнены.",
};

function initials(fullName: string): string {
  return fullName
    .split(" ")
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

export function EmployeeJourneyScreen() {
  const { t } = useI18n();
  const formatLabels = { online: t("online"), offline: t("offline"), self_paced: t("self_paced") };
  const statusLabels = { completed: t("statusCompleted"), in_progress: t("statusInProgress"), dropped: t("statusDropped"), no_show: t("statusNoShow"), declined: t("statusDeclined"), overdue: t("statusOverdue") };
  const [employees, setEmployees] = useState<EmployeeListItem[]>([]);
  const [identity, setIdentity] = useState<AuthIdentity | null>(null);
  const [authVersion, setAuthVersion] = useState(0);
  const [selectedId, setSelectedId] = useState("");
  const [journey, setJourney] = useState<EmployeeJourney | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [completing, setCompleting] = useState<string | null>(null);
  const [changes, setChanges] = useState<SkillChange[]>([]);

  useEffect(() => {
    const onAuthChange = () => setAuthVersion((version) => version + 1);
    window.addEventListener(AUTH_CHANGE_EVENT, onAuthChange);
    return () => window.removeEventListener(AUTH_CHANGE_EVENT, onAuthChange);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setIdentity(null);
    setSelectedId("");
    setEmployees([]);
    setJourney(null);
    setLoading(true);
    setError(null);
    fetchAuthIdentity(controller.signal)
      .then(async (auth) => {
        if (controller.signal.aborted) return;
        setIdentity(auth);
        if (auth.role === "employee") {
          if (!auth.employee_id) throw new Error("Токен не привязан к сотруднику");
          setSelectedId(auth.employee_id);
          return;
        }
        const items = await fetchEmployees(controller.signal);
        if (controller.signal.aborted) return;
        setEmployees(items);
        setSelectedId(items[0]?.employee_id ?? "");
        if (items.length === 0) setLoading(false);
      })
      .catch((requestError: unknown) => {
        if (requestError instanceof Error && requestError.name !== "AbortError") {
          setError(requestError.message);
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, [authVersion]);

  useEffect(() => {
    if (!selectedId || !identity) return;
    const controller = new AbortController();
    setJourney(null);
    setLoading(true);
    setError(null);
    setChanges([]);
    fetchEmployeeJourney(selectedId, controller.signal)
      .then(setJourney)
      .catch((requestError: unknown) => {
        if (requestError instanceof Error && requestError.name !== "AbortError") {
          setError(requestError.message);
        }
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [identity, selectedId]);

  const selectedEmployee = useMemo(
    () => employees.find((item) => item.employee_id === selectedId),
    [employees, selectedId],
  );

  async function handleComplete(eventId: string) {
    if (!journey || journey.employee.employee_id !== selectedId) return;
    setCompleting(eventId);
    setError(null);
    try {
      const result = await completeActivity(
        journey.employee.employee_id,
        eventId,
        crypto.randomUUID(),
      );
      setJourney(result.journey);
      setChanges(result.changes);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Не удалось завершить активность");
    } finally {
      setCompleting(null);
    }
  }

  if (error && !journey) {
    return (
      <main className="page-content">
        <section className="error-panel">
          <span>{t("apiUnavailable")}</span>
          <h1>{t("loadingFailed")}</h1>
          <p>{error}</p>
          <button onClick={() => window.location.reload()} type="button">{t("retry")}</button>
        </section>
      </main>
    );
  }

  if (!loading && identity?.role === "hr" && employees.length === 0) {
    return (
      <main className="page-content">
        <section className="compact-empty">Профили сотрудников пока не загружены.</section>
      </main>
    );
  }

  if (loading || !journey) {
    return (
      <main className="page-content" aria-busy="true">
        <div className="skeleton heading-skeleton" />
        <div className="skeleton hero-skeleton" />
        <div className="card-grid">
          <div className="skeleton card-skeleton" />
          <div className="skeleton card-skeleton" />
          <div className="skeleton card-skeleton" />
        </div>
      </main>
    );
  }

  const { employee, progress } = journey;
  const completedActivities = journey.activity_history.filter((item) => item.status === "completed");

  return (
    <main className="page-content">
      <div className="workspace-row">
        <div className="eyebrow">{t("journey")} · dataset v{journey.dataset_version}</div>
        {identity?.role === "hr" && <label className="employee-picker">
          <span>{t("demoUser")}</span>
          <select value={selectedId} onChange={(event) => setSelectedId(event.target.value)}>
            {employees.map((item) => (
              <option key={item.employee_id} value={item.employee_id}>
                {item.employee_id} · {item.full_name} · {item.grade}
              </option>
            ))}
          </select>
        </label>}
      </div>

      <div className="page-heading">
        <div>
          <h1>{t("greeting")}, {employee.full_name.split(" ")[0]}</h1>
          <p>{t("calculated")} {journey.as_of_date}.</p>
        </div>
        <span className="status-pill">{t("realData")}</span>
      </div>

      {error && <div className="inline-error">{error}</div>}
      {journey.recommendation_notice && (
        <div className={`ai-notice ${journey.recommendation_mode}`} aria-live="polite">
          <strong>{journey.recommendation_mode === "ai" ? "AI подключён" : "Fallback-режим"}</strong>
          <span>{journey.recommendation_notice}</span>
        </div>
      )}
      {changes.length > 0 && (
        <section className="success-panel" aria-live="polite">
          <strong>{t("progressUpdated")}</strong>
          <div>
            {changes.map((change) => (
              <span key={change.skill_id}>
                {change.name}: {change.before} → {change.after}
              </span>
            ))}
          </div>
        </section>
      )}

      <section className="trajectory-panel">
        <div className="employee-summary">
          <span className="employee-initials">{initials(employee.full_name)}</span>
          <div>
            <span className="section-kicker">{t("currentRole")}</span>
            <h2>{employee.role}</h2>
            <p>{employee.grade} · {employee.department}</p>
            <p>{t("tenure")}: {employee.tenure_months == null ? "—" : `${employee.tenure_months} ${t("months")}`}</p>
            {employee.hire_date && <p>{t("hiredOn")}: {employee.hire_date}</p>}
          </div>
        </div>
        <div className="trajectory-progress">
          <div className="progress-heading">
            <span>{t("readiness")}: {journey.target_role} {journey.target_grade}</span>
            <strong>{progress.percentage}%</strong>
          </div>
          <div className="progress-track" aria-label={`Готовность ${progress.percentage}%`}>
            <span style={{ width: `${progress.percentage}%` }} />
          </div>
          <div className="grade-route">
            <span className="grade active">{employee.grade}</span>
            <span className="route-line" />
            <span className="grade target">{journey.target_grade}</span>
          </div>
          <small className="progress-basis">
            {progress.current_points} из {progress.required_points} требуемых уровней навыков
          </small>
        </div>
      </section>

      <section className="section-block" data-testid="current-skills">
        <div className="section-heading">
          <div><span className="section-kicker">{t("currentRole")}</span><h2>{t("currentSkills")}</h2></div>
          <span className="count-label">{journey.current_skills.length} {t("skills")}</span>
        </div>
        <div className="current-skill-grid">
          {journey.current_skills.map((skill) => (
            <article className="current-skill-card" key={skill.skill_id}>
              <span>{skill.skill_id}</span><strong>{skill.name}</strong><b>{t("skillLevel")} {skill.level}/5</b>
            </article>
          ))}
        </div>
      </section>

      <section className="section-block" data-testid="completed-activities">
        <div className="section-heading">
          <div><span className="section-kicker">{employee.full_name}</span><h2>{t("completedActivities")}</h2></div>
          <span className="count-label">{completedActivities.length}</span>
        </div>
        {completedActivities.length ? (
          <div className="completed-activity-list">
            {completedActivities.map((activity) => (
              <article className="completed-activity-card" key={activity.record_id}>
                <div><strong>{activity.title}</strong><span>{activity.event_id} · {t("completedOn")} {activity.activity_date}</span></div>
                <div className="activity-results"><b>{activity.completion_pct}%</b>{activity.score !== null && <span>{t("score")}: {activity.score}</span>}{activity.feedback_rating !== null && <span>{t("feedback")}: {activity.feedback_rating}/5</span>}</div>
              </article>
            ))}
          </div>
        ) : <div className="compact-empty">{t("noCompleted")}</div>}
      </section>

      <section className="section-block" data-testid="participation-history">
        <div className="section-heading">
          <h2>{t("participationHistory")}</h2>
          <span className="count-label">{journey.activity_history.length}</span>
        </div>
        {journey.activity_history.length ? (
          <div className="completed-activity-list">
            {journey.activity_history.map((activity) => (
              <article className="completed-activity-card" key={activity.record_id}>
                <div><strong>{activity.title}</strong><span>{activity.event_id} · {activity.activity_date}</span></div>
                <div className="activity-results"><strong>{statusLabels[activity.status]}</strong><span>{activity.completion_pct}%</span></div>
              </article>
            ))}
          </div>
        ) : <div className="compact-empty">{t("noHistory")}</div>}
      </section>

      {journey.continuations.length > 0 && (
        <section className="section-block">
          <div className="section-heading">
            <div>
              <span className="section-kicker">{t("started")}</span>
              <h2>{t("continue")}</h2>
            </div>
          </div>
          <div className="continuation-grid">
            {journey.continuations.map((item) => (
              <article className="continuation-card" key={item.event_id}>
                <div><strong>{item.title}</strong><span>{item.event_id}</span></div>
                <b>{item.completion_pct}%</b>
              </article>
            ))}
          </div>
        </section>
      )}

      <section className="section-block">
        <div className="section-heading">
          <div>
            <span className="section-kicker">{t("focus")}</span>
            <h2>{t("gaps")} {journey.target_grade}</h2>
          </div>
          <span className="count-label">{journey.skill_gaps.length} {t("skills")}</span>
        </div>
        {journey.skill_gaps.length ? (
          <div className="gap-grid">
            {journey.skill_gaps.map((gap) => (
              <article className="gap-card" key={gap.skill_id}>
                <div>
                  <h3>{gap.name}</h3>
                  {gap.critical && <span className="critical-label">{t("critical")}</span>}
                </div>
                <div className="level-row">
                  <strong>{gap.current_level}</strong>
                  <span className="level-line"><i style={{ width: `${(gap.current_level / gap.required_level) * 100}%` }} /></span>
                  <strong>{gap.required_level}</strong>
                </div>
                <p>{t("gap")}: {gap.gap}</p>
              </article>
            ))}
          </div>
        ) : <div className="compact-empty">Все требования целевого профиля выполнены.</div>}
      </section>

      <section className="section-block">
        <div className="section-heading">
          <div>
            <span className="section-kicker">
              {journey.recommendation_mode === "ai" ? t("ai") : t("deterministic")}
            </span>
            <h2>{t("nextSteps")}</h2>
          </div>
          <p className="explainability-note">Score раскрывается до отдельных факторов</p>
        </div>
        {journey.recommendations.length ? (
          <div className="recommendation-list">
            {journey.recommendations.map((recommendation, index) => (
              <article className="recommendation-card" key={recommendation.event_id}>
                <div className="recommendation-rank">0{index + 1}</div>
                <div className="recommendation-main">
                  <div className="recommendation-meta">
                    <span>{formatLabels[recommendation.event_format]}</span>
                    <span>{recommendation.duration_hours} ч</span>
                    <span>{recommendation.kind === "bridge" ? "Bridge" : recommendation.event_id}</span>
                  </div>
                  <h3>{recommendation.title}</h3>
                  <div className="impact-line">
                    <span>{recommendation.skill}</span>
                    <strong>{recommendation.current_level} → {recommendation.projected_level}</strong>
                    <small>{t("target")} {recommendation.required_level}</small>
                  </div>
                  <details>
                    <summary>{t("why")}</summary>
                    <ul>{recommendation.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
                    <div className="factor-grid">
                      {recommendation.factors.map((factor) => (
                        <span key={factor.code}>{factor.label}<b>{Math.round(factor.value * 100)}%</b></span>
                      ))}
                    </div>
                  </details>
                </div>
                <div className="score-block">
                  <span>{t("relevance")}</span>
                  <strong>{recommendation.score}</strong>
                  {identity?.role === "employee" && <button
                      disabled={completing !== null || journey.employee.employee_id !== selectedId}
                      onClick={() => handleComplete(recommendation.event_id)}
                      type="button"
                    >
                      {completing === recommendation.event_id ? t("updating") : t("complete")}
                    </button>}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="compact-empty">
            {emptyReasonLabels[journey.primary_reason ?? ""] ?? "Новый шаг пока не найден."}
          </div>
        )}
      </section>

      <span className="sr-only">Выбран: {selectedEmployee?.full_name ?? journey.employee.full_name}</span>
    </main>
  );
}
