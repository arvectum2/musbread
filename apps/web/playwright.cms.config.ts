import { defineConfig, devices } from "@playwright/test";

if (!process.env.MUSBREAD_E2E_BASE_URL || !process.env.MUSBREAD_E2E_PASSWORD) {
  throw new Error("Isolated QA harness is required; run python3 scripts/qa_cms_browser.py");
}

export default defineConfig({
  testDir: "./cms-e2e",
  timeout: 25_000,
  workers: 1,
  reporter: process.env.CI ? "github" : "list",
  use: {
    ...devices["Desktop Chrome"],
    baseURL: process.env.MUSBREAD_E2E_BASE_URL,
    screenshot: "only-on-failure",
    trace: "on-first-retry",
  },
});
