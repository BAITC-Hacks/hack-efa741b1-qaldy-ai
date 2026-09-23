import { test as base, expect, type Route } from "@playwright/test";
import {
  completionFixture,
  employeeFixture,
  journeyFixture,
} from "../../src/test/fixtures";

async function handleApiRoute(route: Route) {
  const request = route.request();
  const url = new URL(request.url());
  const { pathname } = url;

  if (request.method() === "GET" && pathname === "/api/v1/employees") {
    await route.fulfill({ json: [employeeFixture] });
    return;
  }

  if (
    request.method() === "POST" &&
    /^\/api\/v1\/employees\/[^/]+\/recommendations$/.test(pathname)
  ) {
    await route.fulfill({ json: journeyFixture });
    return;
  }

  if (
    request.method() === "POST" &&
    /^\/api\/v1\/employees\/[^/]+\/activities\/[^/]+\/complete$/.test(pathname)
  ) {
    await route.fulfill({ json: completionFixture });
    return;
  }

  await route.fulfill({
    status: 404,
    json: { detail: `Нет mock-обработчика для ${request.method()} ${pathname}` },
  });
}

export const test = base.extend<{ mockNetwork: void }>({
  mockNetwork: [
    async ({ context }, use) => {
      await context.addInitScript(() => {
        window.localStorage.clear();
        window.sessionStorage.clear();
      });

      await context.route("**/*", async (route) => {
        const url = new URL(route.request().url());

        if (url.pathname.startsWith("/api/v1/")) {
          await handleApiRoute(route);
          return;
        }

        if (
          url.protocol === "data:" ||
          url.protocol === "blob:" ||
          url.hostname === "127.0.0.1" ||
          url.hostname === "localhost"
        ) {
          await route.continue();
          return;
        }

        await route.abort("blockedbyclient");
      });

      await use();
    },
    { auto: true },
  ],
});

export { expect };
