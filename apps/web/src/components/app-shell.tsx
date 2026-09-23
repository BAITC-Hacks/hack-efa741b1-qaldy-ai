import Link from "next/link";
import type { ReactNode } from "react";

const navigation = [
  { href: "/", label: "Мой путь", marker: "01" },
  { href: "/hr", label: "HR-аналитика", marker: "02" },
  { href: "/import", label: "Импорт данных", marker: "03" },
];

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="app-shell">
      <header className="topbar">
        <Link className="brand" href="/">
          <span className="brand-mark">Q</span>
          <span>
            <strong>QALDY AI</strong>
            <small>Career Quest</small>
          </span>
        </Link>
        <nav aria-label="Основная навигация">
          {navigation.map((item) => (
            <Link href={item.href} key={item.href}>
              <span>{item.marker}</span>
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="topbar-actions">
          <button className="language-button" type="button" aria-label="Язык интерфейса">
            RU
          </button>
          <div className="avatar" aria-label="Профиль Марата Есенова">МЕ</div>
        </div>
      </header>
      {children}
    </div>
  );
}
