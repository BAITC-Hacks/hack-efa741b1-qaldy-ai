"use client";

import { useCallback, useEffect, useState } from "react";
import { useI18n } from "@/lib/i18n";
import { AUTH_CHANGE_EVENT, fetchAuthIdentity, getAuthHeaders } from "@/lib/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const modules = [
  { id: "skill-gaps", ru: "Дефициты навыков", kk: "Дағды тапшылығы", en: "Skill gaps" },
  { id: "participation", ru: "Участие", kk: "Қатысу", en: "Participation" },
  { id: "uncovered-employees", ru: "Нет следующего шага", kk: "Келесі қадам жоқ", en: "Uncovered employees" },
  { id: "catalog-gaps", ru: "Пробелы каталога", kk: "Каталог олқылықтары", en: "Catalog gaps" },
] as const;

type Row = Record<string, unknown>;
function rowsOf(value: unknown): Row[] {
  if (Array.isArray(value)) return value.filter((item): item is Row => Boolean(item) && typeof item === "object");
  if (!value || typeof value !== "object") return [];
  const object = value as Row;
  // Participation keeps its event rows in by_event and leaves items empty.
  for (const key of ["by_event", "items", "results", "data", "rows"]) {
    if (Array.isArray(object[key])) return rowsOf(object[key]);
    const rows = rowsOf(object[key]);
    if (rows.length) return rows;
  }
  return [object];
}
function display(value: unknown) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export default function HrPage() {
  const { locale } = useI18n();
  const [active, setActive] = useState<(typeof modules)[number]["id"]>("skill-gaps");
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [authVersion, setAuthVersion] = useState(0);
  const labels = {
    ru: { eyebrow: "HR workspace", title: "Командное развитие", text: "Актуальные метрики из HR API.", refresh: "Обновить", empty: "Данных пока нет", error: "Не удалось загрузить HR-метрики" },
    kk: { eyebrow: "HR кеңістігі", title: "Команданы дамыту", text: "HR API-дан өзекті көрсеткіштер.", refresh: "Жаңарту", empty: "Дерек жоқ", error: "HR көрсеткіштері жүктелмеді" },
    en: { eyebrow: "HR workspace", title: "Team development", text: "Current metrics from the HR API.", refresh: "Refresh", empty: "No data yet", error: "Could not load HR metrics" },
  }[locale];

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const identity = await fetchAuthIdentity();
      if (identity.role !== "hr") throw new Error("Для HR-аналитики требуется HR-токен");
      const response = await fetch(`${API_URL}/api/v1/hr/${active}`, { headers: getAuthHeaders() });
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
      setRows(rowsOf(await response.json()));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : labels.error); setRows([]);
    } finally { setLoading(false); }
  }, [active, labels.error]);
  useEffect(() => {
    const onAuthChange = () => setAuthVersion((version) => version + 1);
    window.addEventListener(AUTH_CHANGE_EVENT, onAuthChange);
    return () => window.removeEventListener(AUTH_CHANGE_EVENT, onAuthChange);
  }, []);
  useEffect(() => { void load(); }, [load, authVersion]);
  const columns = Array.from(new Set(rows.flatMap((row) => Object.keys(row)))).slice(0, 7);

  return (
    <main className="page-content" data-testid="hr-dashboard">
      <div className="eyebrow">{labels.eyebrow}</div>
      <div className="page-heading"><div><h1>{labels.title}</h1><p>{labels.text}</p></div><button className="secondary-action" onClick={load} type="button">{labels.refresh}</button></div>
      <div className="dashboard-tabs" role="tablist">
        {modules.map((module) => <button aria-selected={active === module.id} key={module.id} onClick={() => setActive(module.id)} role="tab" type="button">{module[locale]}</button>)}
      </div>
      <section className="data-panel" aria-busy={loading}>
        {loading ? <div className="skeleton card-skeleton" /> : error ? <div className="inline-error">{labels.error}: {error}</div> : rows.length === 0 ? <div className="compact-empty">{labels.empty}</div> : (
          <div className="table-scroll"><table><thead><tr>{columns.map((column) => <th key={column}>{column.replaceAll("_", " ")}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={String(row.id ?? row.employee_id ?? row.skill_id ?? row.key ?? index)}>{columns.map((column) => <td key={column}>{display(row[column])}</td>)}</tr>)}</tbody></table></div>
        )}
      </section>
    </main>
  );
}
