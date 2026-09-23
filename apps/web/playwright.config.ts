import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3100";

export default defineConfig({
  testDir: "./tests",
  outputDir: "./test-results",
  fullyParallel: false,
  timeout: 60_000,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI
    ? [["line"], ["html", { open: "never" }]]
    : [["list"], ["html", { open: "never" }]],
  expect: {
    timeout: 10_000,
    toHaveScreenshot: {
      animations: "disabled",
      caret: "hide",
      maxDiffPixelRatio: 0.05,
    },
  },
  use: {
    baseURL,
    locale: "ru-RU",
    timezoneId: "Asia/Qyzylorda",
    colorScheme: "light",
    reducedMotion: "reduce",
    trace: "off",
    screenshot: "only-on-failure",
    video: "off",
  },
  projects: [
    {
      name: "e2e",
      testMatch: /.*\.e2e\.spec\.ts/,
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 900 },
      },
    },
    {
      name: "a11y",
      testMatch: /.*\.a11y\.spec\.ts/,
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 900 },
      },
    },
    {
      name: "visual",
      testMatch: /.*\.visual\.spec\.ts/,
      snapshotPathTemplate: "{testDir}/visual/__snapshots__/{arg}{ext}",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1672, height: 941 },
        deviceScaleFactor: 1,
      },
    },
  ],
  webServer: {
    command: "node .next/standalone/server.js",
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: {
      ...process.env,
      HOSTNAME: "127.0.0.1",
      PORT: "3100",
      NEXT_PUBLIC_USE_FIXTURES: "1",
      NEXT_PUBLIC_API_URL: "http://localhost:8000",
    },
  },
});
