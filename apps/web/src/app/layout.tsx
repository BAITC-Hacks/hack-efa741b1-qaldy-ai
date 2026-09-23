import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppShell } from "@/components/app-shell";
import { I18nProvider } from "@/lib/i18n";

import "./globals.css";

export const metadata: Metadata = {
  title: "QALDY AI — Career Quest",
  description: "Объяснимый AI-навигатор развития сотрудника",
  icons: {
    icon: "/halyk-mark-official.png",
    apple: "/halyk-mark-official.png",
  },
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="ru">
      <body>
        <I18nProvider><AppShell>{children}</AppShell></I18nProvider>
      </body>
    </html>
  );
}
