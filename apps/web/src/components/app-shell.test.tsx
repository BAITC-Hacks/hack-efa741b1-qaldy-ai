import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { I18nProvider } from "@/lib/i18n";
import { AppShell } from "./app-shell";

const navigationState = vi.hoisted(() => ({ pathname: "/career-map" }));

vi.mock("next/navigation", () => ({
  usePathname: () => navigationState.pathname,
}));

const requiredLinks = [
  ["Главная", "/"],
  ["Моя карьерная карта", "/career-map"],
  ["Квесты", "/quests"],
  ["Навыки", "/skills"],
  ["Обучение", "/learning"],
  ["Возможности", "/opportunities"],
  ["Команда", "/team"],
  ["Библиотека", "/library"],
  ["AI-навигатор", "/ai-navigator"],
] as const;

function renderShell() {
  return render(
    <I18nProvider>
      <AppShell>
        <main id="main-content">Контент</main>
      </AppShell>
    </I18nProvider>,
  );
}

describe("AppShell navigation", () => {
  beforeEach(() => {
    navigationState.pathname = "/career-map";
  });

  it("exposes all product destinations and marks only the current one", () => {
    renderShell();
    const navigation = screen.getByRole("navigation", { name: "Основная навигация" });

    for (const [name, href] of requiredLinks) {
      expect(within(navigation).getByRole("link", { name })).toHaveAttribute("href", href);
    }
    expect(within(navigation).getByRole("link", { name: "Моя карьерная карта" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(within(navigation).getByRole("link", { name: "Главная" })).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("opens the profile destination from the user menu", async () => {
    const user = userEvent.setup();
    renderShell();

    await user.click(screen.getByRole("button", { name: /Анна Смирнова/ }));

    expect(screen.getByRole("menuitem", { name: "Профиль и достижения" })).toHaveAttribute(
      "href",
      "/profile",
    );
  });

  it("does not highlight Home while the profile page is open", () => {
    navigationState.pathname = "/profile";
    renderShell();

    const navigation = screen.getByRole("navigation", { name: "Основная навигация" });
    expect(within(navigation).queryByRole("link", { current: "page" })).not.toBeInTheDocument();
  });

  it("exposes an operable mobile navigation toggle", async () => {
    const user = userEvent.setup();
    renderShell();
    const toggle = screen.getByRole("button", { name: "Открыть навигацию" });

    expect(toggle).toHaveAttribute("aria-expanded", "false");
    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("button", { name: "Закрыть навигацию" })).toBeInTheDocument();
  });
});
