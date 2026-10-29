import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  timeout: 20_000,
  expect: { timeout: 8_000 },
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? "github" : "list",
  use: {
    ...devices["Desktop Chrome"],
    baseURL: "http://127.0.0.1:18766",
    screenshot: "only-on-failure",
    trace: "on-first-retry",
  },
  webServer: {
    command: "php -S 127.0.0.1:18766 -t out",
    url: "http://127.0.0.1:18766/",
    reuseExistingServer: !process.env.CI,
    timeout: 20_000,
  },
});
