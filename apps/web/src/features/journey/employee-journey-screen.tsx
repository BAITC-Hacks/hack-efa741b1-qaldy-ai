"use client";

import { useEffect, useState } from "react";

import { fetchEmployeeJourney } from "./api";
import type { EmployeeJourney } from "./types";

const formatLabels = {
  online: "Онлайн",
  offline: "Офлайн",
  self_paced: "В своём темпе",
};

export function EmployeeJourneyScreen() {
  const [journey, setJourney] = useState<EmployeeJourney | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchEmployeeJourney(controller.signal)
      .then(setJourney)
      .catch((requestError: unknown) => {
        if (requestError instanceof Error && requestError.name !== "AbortError") {
          setError(requestError.message);
        }
      });
    return () => controller.abort();
  }, []);

  if (error) {
    return (
      <main className="page-content">
        <section className="error-panel">
          <span>API недоступен</span>
          <h1>Не удалось загрузить карьерную траекторию</h1>
          <p>{error}. Проверьте, что backend запущен на порту 8000.</p>
          <button onClick={() => window.location.reload()} type="button">Повторить</button>
        </section>
      </main>
    );
  }

  if (!journey) {
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

  const { employee } = journey;

  return (
    <main className="page-content">
      <div className="eyebrow">Личная траектория · данные {journey.source === "demo" ? "demo" : "профиля"}</div>
      <div className="page-heading">
        <div>
          <h1>Добрый день, {employee.full_name.split(" ")[0]}</h1>
          <p>Ваш следующий лучший шаг рассчитан по карьерной цели, навыкам и истории участия.</p>
        </div>
        <span className="status-pill">Профиль актуален</span>
      </div>

      <section className="trajectory-panel">
        <div className="employee-summary">
          <span className="employee-initials">МЕ</span>
          <div>
            <span className="section-kicker">Текущая позиция</span>
            <h2>{employee.role}</h2>
            <p>{employee.grade} · цель: {employee.target_grade}</p>
          </div>
        </div>
        <div className="trajectory-progress">
          <div className="progress-heading">
            <span>Готовность к переходу</span>
            <strong>{employee.trajectory_progress}%</strong>
          </div>
          <div className="progress-track" aria-label={`Готовность ${employee.trajectory_progress}%`}>
            <span style={{ width: `${employee.trajectory_progress}%` }} />
          </div>
          <div className="grade-route">
            <span className="grade active">{employee.grade}</span>
            <span className="route-line" />
            <span className="grade target">{employee.target_grade}</span>
          </div>
        </div>
      </section>

      <section className="section-block">
        <div className="section-heading">
          <div>
            <span className="section-kicker">Фокус развития</span>
            <h2>Разрывы до {employee.target_grade}</h2>
          </div>
          <span className="count-label">{journey.skill_gaps.length} навыка</span>
        </div>
        <div className="gap-grid">
          {journey.skill_gaps.map((gap) => (
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
              <p>Текущий уровень → требование цели</p>
            </article>
          ))}
        </div>
      </section>

      <section className="section-block">
        <div className="section-heading">
          <div>
            <span className="section-kicker">AI-рекомендации</span>
            <h2>Следующие шаги</h2>
          </div>
          <p className="explainability-note">Каждый шаг подкреплён проверяемыми факторами</p>
        </div>
        <div className="recommendation-list">
          {journey.recommendations.map((recommendation, index) => (
            <article className="recommendation-card" key={recommendation.event_id}>
              <div className="recommendation-rank">0{index + 1}</div>
              <div className="recommendation-main">
                <div className="recommendation-meta">
                  <span>{formatLabels[recommendation.format]}</span>
                  <span>{recommendation.duration_hours} ч</span>
                  <span>{recommendation.event_id}</span>
                </div>
                <h3>{recommendation.title}</h3>
                <div className="impact-line">
                  <span>{recommendation.skill}</span>
                  <strong>{recommendation.current_level} → {recommendation.projected_level}</strong>
                  <small>цель {recommendation.required_level}</small>
                </div>
                <details>
                  <summary>Почему этот шаг</summary>
                  <ul>
                    {recommendation.reasons.map((reason) => <li key={reason}>{reason}</li>)}
                  </ul>
                </details>
              </div>
              <div className="score-block">
                <span>Релевантность</span>
                <strong>{recommendation.score}</strong>
                <button type="button">Подробнее</button>
              </div>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
