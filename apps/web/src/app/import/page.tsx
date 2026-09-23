"use client";

import { useState } from "react";
import { useI18n } from "@/lib/i18n";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Result = Record<string, unknown>;

async function responseJson(response: Response): Promise<Result> {
  const body = await response.json().catch(() => ({})) as Result;
  if (!response.ok) throw new Error(String(body.detail ?? body.message ?? `HTTP ${response.status}`));
  return body;
}

export default function ImportPage() {
  const { locale } = useI18n();
  const [jsonFile, setJsonFile] = useState<File | null>(null);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [validation, setValidation] = useState<Result | null>(null);
  const [applied, setApplied] = useState<Result | null>(null);
  const [busy, setBusy] = useState<"validate" | "apply" | null>(null);
  const [error, setError] = useState("");
  const labels = {
    ru: { title: "Импорт проверочных профилей", text: "Dry-run проверяет файл до изменения SQLite.", choose: "Выберите JSON или CSV", validate: "Проверить", apply: "Применить", valid: "Dry-run завершён", applied: "Импорт применён", error: "Ошибка импорта" },
    kk: { title: "Тексеру профильдерін импорттау", text: "Dry-run SQLite өзгермей тұрып файлды тексереді.", choose: "JSON немесе CSV таңдаңыз", validate: "Тексеру", apply: "Қолдану", valid: "Dry-run аяқталды", applied: "Импорт қолданылды", error: "Импорт қатесі" },
    en: { title: "Import evaluation profiles", text: "Dry-run validates the file before changing SQLite.", choose: "Choose JSON or CSV", validate: "Validate", apply: "Apply", valid: "Dry-run complete", applied: "Import applied", error: "Import error" },
  }[locale];
  const headers = { "X-Demo-Role": "hr" };

  async function validate() {
    if (!jsonFile) return;
    setBusy("validate"); setError(""); setApplied(null);
    try {
      const parsed = JSON.parse(await jsonFile.text()) as Result;
      const payload = "employees_json" in parsed ? parsed : { employees_json: parsed };
      if (csvFile) payload.activity_history_csv = await csvFile.text();
      const response = await fetch(`${API_URL}/api/v1/import/validate`, { method: "POST", headers: { ...headers, "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      setValidation(await responseJson(response));
    } catch (reason) { setError(reason instanceof Error ? reason.message : labels.error); setValidation(null); }
    finally { setBusy(null); }
  }

  async function apply() {
    if (!jsonFile || !validation) return;
    setBusy("apply"); setError("");
    try {
      const response = await fetch(`${API_URL}/api/v1/import/apply`, {
        method: "POST", headers: { ...headers, "Content-Type": "application/json", "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify({ validation_token: validation.validation_token, package_hash: validation.package_hash }),
      });
      setApplied(await responseJson(response));
    } catch (reason) { setError(reason instanceof Error ? reason.message : labels.error); }
    finally { setBusy(null); }
  }

  const mayApply = Boolean(validation && validation.valid !== false && validation.is_valid !== false && validation.ok !== false);
  return (
    <main className="page-content" data-testid="import-workspace">
      <div className="eyebrow">Data workspace</div>
      <div className="page-heading"><div><h1>{labels.title}</h1><p>{labels.text}</p></div></div>
      <section className="import-panel">
        <div className="import-files"><label className="file-drop"><span className="upload-mark">EMPLOYEES.JSON</span><strong>{labels.choose}</strong><input accept=".json,application/json" data-testid="import-file" onChange={(event) => { setJsonFile(event.target.files?.[0] ?? null); setValidation(null); setApplied(null); }} type="file" />{jsonFile && <small>{jsonFile.name} · {Math.ceil(jsonFile.size / 1024)} KB</small>}</label><label className="file-drop"><span className="upload-mark">ACTIVITY_HISTORY.CSV</span><strong>Optional CSV</strong><input accept=".csv,text/csv" onChange={(event) => { setCsvFile(event.target.files?.[0] ?? null); setValidation(null); setApplied(null); }} type="file" />{csvFile && <small>{csvFile.name} · {Math.ceil(csvFile.size / 1024)} KB</small>}</label></div>
        <div className="import-actions"><button disabled={!jsonFile || busy !== null} onClick={validate} type="button">{busy === "validate" ? "…" : labels.validate}</button><button disabled={!mayApply || busy !== null} onClick={apply} type="button">{busy === "apply" ? "…" : labels.apply}</button></div>
        {error && <div className="inline-error" role="alert">{labels.error}: {error}</div>}
        {validation && <ResultPanel title={labels.valid} value={validation} />}
        {applied && <ResultPanel title={labels.applied} value={applied} />}
      </section>
    </main>
  );
}

function ResultPanel({ title, value }: { title: string; value: Result }) {
  return <section className="import-result" aria-live="polite"><h2>{title}</h2><dl>{Object.entries(value).slice(0, 12).map(([key, item]) => <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{typeof item === "object" ? JSON.stringify(item, null, 2) : String(item)}</dd></div>)}</dl></section>;
}
