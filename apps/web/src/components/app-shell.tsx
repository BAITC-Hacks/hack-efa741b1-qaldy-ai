"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { type ReactNode, useEffect, useRef, useState } from "react";

import { type Locale, useI18n } from "@/lib/i18n";
import { AUTH_CHANGE_EVENT, clearAuthToken, fetchAuthIdentity, getAuthToken, setAuthToken, verifyAuthToken, type AuthIdentity } from "@/lib/auth";

const navigation = [
  { href: "/", label: "Главная", labelKey: "home", icon: "home" },
  { href: "/journey", label: "Личная траектория", labelKey: "journey", icon: "map" },
  { href: "/career-map", label: "Моя карьерная карта", icon: "map" },
  { href: "/quests", label: "Квесты", icon: "flag" },
  { href: "/skills", label: "Навыки", icon: "chart" },
  { href: "/learning", label: "Обучение", icon: "cap" },
  { href: "/opportunities", label: "Возможности", icon: "case" },
  { href: "/team", label: "Команда", icon: "team" },
  { href: "/library", label: "Библиотека", icon: "book" },
  { href: "/ai-navigator", label: "AI-навигатор", icon: "ai" },
  { href: "/hr", label: "HR-аналитика", labelKey: "hr", icon: "team" },
  { href: "/import", label: "Импорт", labelKey: "import", icon: "case" },
] as const;

function Glyph({ name }: { name: string }) {
  const paths: Record<string, string> = {
    home: "M4 11 12 4l8 7v9h-6v-6h-4v6H4z",
    map: "m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3zm6-3v15m6-12v15",
    flag: "M5 21V4m0 1h11l-2 4 2 4H5",
    chart: "M4 20V10h4v10zm6 0V4h4v16zm6 0v-7h4v7z",
    cap: "m2 9 10-5 10 5-10 5zm4 3v5c3 3 9 3 12 0v-5",
    case: "M4 7h16v13H4zm5 0V4h6v3m-3 5v3",
    team: "M8 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8m8-1a3 3 0 1 0 0-6m-8 9c-4 0-6 2-6 6h12c0-4-2-6-6-6m8-1c4 0 6 2 6 6h-6",
    book: "M4 4h7a3 3 0 0 1 3 3v13H7a3 3 0 0 0-3 1zm16 0h-3a3 3 0 0 0-3 3v13h3a3 3 0 0 1 3 1z",
    ai: "M8 4h8a4 4 0 0 1 4 4v7a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4V8a4 4 0 0 1 4-4m1 7h.01M15 11h.01M9 15h6M12 4V1",
  };
  return <svg aria-hidden="true" className="nav-glyph" viewBox="0 0 24 24"><path d={paths[name] ?? paths.chart} /></svg>;
}

function BrandMark() {
  return (
    <Image
      alt=""
      aria-hidden="true"
      className="brand-symbol"
      height={44}
      priority
      src="/halyk-mark-official.png"
      width={44}
    />
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { locale, setLocale, t } = useI18n();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [identity, setIdentity] = useState<AuthIdentity | null>(null);
  const [tokenInput, setTokenInput] = useState("");
  const [authError, setAuthError] = useState("");
  const [authBusy, setAuthBusy] = useState(false);
  const [authVersion, setAuthVersion] = useState(0);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onAuthChange = () => setAuthVersion((version) => version + 1);
    window.addEventListener(AUTH_CHANGE_EVENT, onAuthChange);
    return () => window.removeEventListener(AUTH_CHANGE_EVENT, onAuthChange);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    if (!getAuthToken()) {
      setIdentity(null);
      return () => controller.abort();
    }
    fetchAuthIdentity(controller.signal)
      .then(setIdentity)
      .catch((error: unknown) => {
        if (error instanceof Error && error.name !== "AbortError") {
          setIdentity(null);
          setAuthError(error.message);
        }
      });
    return () => controller.abort();
  }, [authVersion]);

  async function signIn(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!tokenInput.trim()) return;
    setAuthBusy(true);
    setAuthError("");
    try {
      const verified = await verifyAuthToken(tokenInput);
      setAuthToken(tokenInput);
      setIdentity(verified);
      setTokenInput("");
      setProfileOpen(false);
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Не удалось проверить токен");
    } finally {
      setAuthBusy(false);
    }
  }

  useEffect(() => {
    setDrawerOpen(false);
    setProfileOpen(false);
  }, [pathname]);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setDrawerOpen(false);
        setProfileOpen(false);
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">К основному содержимому</a>
      <header className="topbar">
        <button aria-expanded={drawerOpen} aria-label="Открыть навигацию" className="mobile-menu-button" onClick={() => setDrawerOpen((value) => !value)} type="button">
          <span /><span /><span />
        </button>
        <Link className="brand" href="/" aria-label="Halyk Career Quest — главная">
          <BrandMark /><strong>Halyk</strong><i /><span>CAREER QUEST</span>
        </Link>
        <label className="global-search">
          <span className="sr-only">Глобальный поиск</span>
          <svg aria-hidden="true" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7" /><path d="m16 16 5 5" /></svg>
          <input placeholder="Поиск по навыкам, курсам, возможностям..." type="search" />
        </label>
        <div className="topbar-actions" ref={menuRef}>
          <label className="locale-picker">
            <span className="sr-only">{t("language")}</span>
            <select aria-label={t("language")} onChange={(event) => setLocale(event.target.value as Locale)} value={locale}>
              <option value="ru">RU</option><option value="kk">KK</option><option value="en">EN</option>
            </select>
          </label>
          <button aria-label="Уведомления: 3 демонстрационных" className="notification-button" type="button">
            <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" /></svg><b>3</b>
          </button>
          <span className="header-divider" />
          <button aria-expanded={profileOpen} aria-haspopup="menu" className="profile-trigger" onClick={() => setProfileOpen((value) => !value)} type="button">
            <span className="avatar-photo">{identity?.role === "hr" ? "HR" : identity?.employee_id?.slice(0, 2).toUpperCase() ?? "ДЕ"}</span>
            <span><strong>{identity?.role === "hr" ? "HR-доступ" : identity?.employee_id ?? "Демо-профиль"}</strong><small>{identity ? "Подключено к API" : "Войдите с демо-токеном"}</small></span>
            <svg aria-hidden="true" viewBox="0 0 24 24"><path d="m8 10 4 4 4-4" /></svg>
          </button>
          {profileOpen && (
            <div className="profile-menu" role="menu">
              <Link href="/profile" role="menuitem">Профиль и достижения</Link>
              <form className="auth-menu-form" onSubmit={signIn}>
                <label htmlFor="demo-auth-token">Демо-токен API</label>
                <input id="demo-auth-token" className="auth-token-input" type="password" autoComplete="off" value={tokenInput} onChange={(event) => setTokenInput(event.target.value)} placeholder="Вставьте токен" />
                <button disabled={authBusy || !tokenInput.trim()} type="submit">{authBusy ? "Проверка…" : "Подключиться"}</button>
                {authError && <span className="auth-menu-error" role="alert">{authError}</span>}
              </form>
              {identity && <button role="menuitem" type="button" onClick={() => { clearAuthToken(); setIdentity(null); setProfileOpen(false); }}>Выйти</button>}
            </div>
          )}
        </div>
      </header>

      <div className="app-body">
        {drawerOpen && <button aria-label="Закрыть навигацию" className="drawer-backdrop" onClick={() => setDrawerOpen(false)} type="button" />}
        <aside className={`sidebar ${drawerOpen ? "is-open" : ""}`}>
          <div className="level-card">
            <div className="sidebar-demo-label">Демо: уровень и XP приведены для примера</div>
            <div className="level-row-top">
              <span className="sidebar-avatar">{identity?.role === "hr" ? "HR" : identity?.employee_id?.slice(0, 2).toUpperCase() ?? "ДЕ"}</span>
              <div><strong>Уровень 7</strong><div className="xp-track"><i style={{ width: "77%" }} /></div><small>2 450 / 3 000 XP</small></div>
            </div>
            <div className="streak-row"><span className="flame-mark">◆</span><strong>Серия: 4 недели</strong><span>›</span></div>
          </div>
          <nav aria-label="Основная навигация" className="sidebar-nav">
            {navigation.map((item) => {
              const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
              return (
                <Link aria-current={active ? "page" : undefined} className={active ? "active" : ""} href={item.href} key={item.href}>
                  <Glyph name={item.icon} /><span>{"labelKey" in item ? t(item.labelKey) : item.label}</span>
                </Link>
              );
            })}
          </nav>
          <div className="sidebar-promo">
            <div className="promo-shape" />
            <strong>Больше<br />возможностей<br />впереди!</strong>
            <p>Развивайтесь.<br />Исследуйте. Достигайте.</p>
          </div>
        </aside>
        <div className="main-column">{children}</div>
      </div>
    </div>
  );
}
