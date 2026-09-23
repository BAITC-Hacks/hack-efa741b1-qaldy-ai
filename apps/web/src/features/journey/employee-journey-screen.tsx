"use client";

import { useEffect, useMemo, useState } from "react";

import { completeActivity, fetchEmployeeJourney, fetchEmployees } from "./api";
import type { EmployeeJourney, EmployeeListItem, SkillChange } from "./types";

const formatLabels = {
  online: "Онлайн",
  offline: "Офлайн",
  self_paced: "В своём темпе",
};

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
  const [employees, setEmployees] = useState<EmployeeListItem[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [journey, setJourney] = useState<EmployeeJourney | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [completing, setCompleting] = useState<string | null>(null);
  const [changes, setChanges] = useState<SkillChange[]>([]);

  useEffect(() => {
    const controller = new AbortController();
    fetchEmployees(controller.signal)
      .then((items) => {
        setEmployees(items);
        setSelectedId(items[0]?.employee_id ?? "");
      })
      .catch((requestError: unknown) => {
        if (requestError instanceof Error && requestError.name !== "AbortError") {
          setError(requestError.message);
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    const controller = new AbortController();
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
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [selectedId]);

  const selectedEmployee = useMemo(
    () => employees.find((item) => item.employee_id === selectedId),
    [employees, selectedId],
  );

  async function handleComplete(eventId: string) {
    if (!journey) return;
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
          <span>API недоступен</span>
          <h1>Не удалось загрузить карьерную траекторию</h1>
          <p>{error}</p>
          <button onClick={() => window.location.reload()} type="button">Повторить</button>
        </section>
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

  return (
    <main className="page-content">
      <div className="workspace-row">
        <div className="eyebrow">Личная траектория · dataset v{journey.dataset_version}</div>
        <label className="employee-picker">
          <span>Демо-пользователь</span>
          <select value={selectedId} onChange={(event) => setSelectedId(event.target.value)}>
            {employees.map((item) => (
              <option key={item.employee_id} value={item.employee_id}>
                {item.employee_id} · {item.full_name} · {item.grade}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="page-heading">
        <div>
          <h1>Добрый день, {employee.full_name.split(" ")[0]}</h1>
          <p>Следующие шаги рассчитаны по карьерной цели, навыкам и истории участия на {journey.as_of_date}.</p>
        </div>
        <span className="status-pill">Реальные seed-данные</span>
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
          <strong>Прогресс обновлён</strong>
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
            <span className="section-kicker">Текущая позиция</span>
            <h2>{employee.role}</h2>
            <p>{employee.grade} · {employee.department}</p>
          </div>
        </div>
        <div className="trajectory-progress">
          <div className="progress-heading">
            <span>Готовность к {journey.target_role} {journey.target_grade}</span>
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

      {journey.continuations.length > 0 && (
        <section className="section-block">
          <div className="section-heading">
            <div>
              <span className="section-kicker">Уже начато</span>
              <h2>Продолжить развитие</h2>
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
            <span className="section-kicker">Фокус развития</span>
            <h2>Разрывы до {journey.target_grade}</h2>
          </div>
          <span className="count-label">{journey.skill_gaps.length} навыков</span>
        </div>
        {journey.skill_gaps.length ? (
          <div className="gap-grid">
            {journey.skill_gaps.slice(0, 6).map((gap) => (
              <article className="gap-card" key={gap.skill_id}>
                <div>
                  <h3>{gap.name}</h3>
                  {gap.critical && <span className="critical-label">Критичный</span>}
                </div>
                <div className="level-row">
                  <strong>{gap.current_level}</strong>
                  <span className="level-line"><i style={{ width: `${(gap.current_level / gap.required_level) * 100}%` }} /></span>
                  <strong>{gap.required_level}</strong>
                </div>
                <p>Разрыв: {gap.gap} · текущий уровень → требование цели</p>
              </article>
            ))}
          </div>
        ) : <div className="compact-empty">Все требования целевого профиля выполнены.</div>}
      </section>

      <section className="section-block">
        <div className="section-heading">
          <div>
            <span className="section-kicker">
              {journey.recommendation_mode === "ai" ? "AI-рекомендации" : "Детерминированные рекомендации"}
            </span>
            <h2>Следующие шаги</h2>
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
                    <small>цель {recommendation.required_level}</small>
                  </div>
                  <details>
                    <summary>Почему этот шаг</summary>
                    <ul>{recommendation.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
                    <div className="factor-grid">
                      {recommendation.factors.map((factor) => (
                        <span key={factor.code}>{factor.label}<b>{Math.round(factor.value * 100)}%</b></span>
                      ))}
                    </div>
                  </details>
                </div>
                <div className="score-block">
                  <span>Релевантность</span>
                  <strong>{recommendation.score}</strong>
                  <button
                    disabled={completing !== null}
                    onClick={() => handleComplete(recommendation.event_id)}
                    type="button"
                  >
                    {completing === recommendation.event_id ? "Обновляем…" : "Завершить"}
                  </button>
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

      <span className="sr-only">Выбран: {selectedEmployee?.full_name}</span>
    </main>
  );
}
