"use client";

import { createContext, type ReactNode, useContext, useEffect, useMemo, useState } from "react";

export type Locale = "ru" | "kk" | "en";

const messages = {
  ru: {
    home: "Главная", hr: "HR-аналитика", import: "Импорт", language: "Язык",
    journey: "Личная траектория", demoUser: "Демо-пользователь", greeting: "Добрый день",
    calculated: "Следующие шаги рассчитаны по карьерной цели, навыкам и истории участия.",
    realData: "Реальные данные", currentRole: "Текущая позиция", readiness: "Готовность",
    started: "Уже начато", continue: "Продолжить развитие", focus: "Фокус развития",
    gaps: "Разрывы до", skills: "навыков", critical: "Критичный", gap: "Разрыв",
    nextSteps: "Следующие шаги", why: "Почему этот шаг", relevance: "Релевантность",
    complete: "Завершить", updating: "Обновляем…", progressUpdated: "Прогресс обновлён",
    retry: "Повторить", apiUnavailable: "API недоступен", loadingFailed: "Не удалось загрузить траекторию",
    deterministic: "Детерминированные рекомендации", ai: "AI-рекомендации", online: "Онлайн",
    offline: "Офлайн", self_paced: "В своём темпе", target: "цель",
  },
  kk: {
    home: "Басты бет", hr: "HR-талдау", import: "Импорт", language: "Тіл",
    journey: "Жеке траектория", demoUser: "Демо-пайдаланушы", greeting: "Қайырлы күн",
    calculated: "Келесі қадамдар мансаптық мақсат, дағдылар және қатысу тарихы бойынша есептелді.",
    realData: "Нақты деректер", currentRole: "Қазіргі лауазым", readiness: "Дайындық",
    started: "Басталған", continue: "Дамуды жалғастыру", focus: "Даму фокусы",
    gaps: "Деңгейге дейінгі алшақтық", skills: "дағды", critical: "Маңызды", gap: "Алшақтық",
    nextSteps: "Келесі қадамдар", why: "Неліктен осы қадам", relevance: "Сәйкестік",
    complete: "Аяқтау", updating: "Жаңартылуда…", progressUpdated: "Прогресс жаңартылды",
    retry: "Қайталау", apiUnavailable: "API қолжетімсіз", loadingFailed: "Траектория жүктелмеді",
    deterministic: "Детерминирленген ұсынымдар", ai: "AI ұсынымдары", online: "Онлайн",
    offline: "Офлайн", self_paced: "Өз қарқынымен", target: "мақсат",
  },
  en: {
    home: "Home", hr: "HR analytics", import: "Import", language: "Language",
    journey: "Personal journey", demoUser: "Demo user", greeting: "Hello",
    calculated: "Next steps are calculated from the career goal, skills and participation history.",
    realData: "Live data", currentRole: "Current role", readiness: "Readiness",
    started: "In progress", continue: "Continue development", focus: "Development focus",
    gaps: "Gaps to", skills: "skills", critical: "Critical", gap: "Gap",
    nextSteps: "Next steps", why: "Why this step", relevance: "Relevance",
    complete: "Complete", updating: "Updating…", progressUpdated: "Progress updated",
    retry: "Retry", apiUnavailable: "API unavailable", loadingFailed: "Could not load journey",
    deterministic: "Deterministic recommendations", ai: "AI recommendations", online: "Online",
    offline: "Offline", self_paced: "Self-paced", target: "target",
  },
} as const;

type Key = keyof typeof messages.ru;
type I18nValue = { locale: Locale; setLocale: (locale: Locale) => void; t: (key: Key) => string };
const I18nContext = createContext<I18nValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("ru");
  useEffect(() => {
    const saved = window.localStorage.getItem("qaldy-locale");
    if (saved === "ru" || saved === "kk" || saved === "en") setLocaleState(saved);
  }, []);
  const setLocale = (next: Locale) => {
    setLocaleState(next);
    window.localStorage.setItem("qaldy-locale", next);
    document.documentElement.lang = next;
  };
  const value = useMemo(() => ({ locale, setLocale, t: (key: Key) => messages[locale][key] }), [locale]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const value = useContext(I18nContext);
  if (!value) throw new Error("useI18n must be used inside I18nProvider");
  return value;
}
