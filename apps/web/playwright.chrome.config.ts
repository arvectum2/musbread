import { defineConfig, devices } from "@playwright/test";
import baseConfig from "./playwright.config";

// Runs the installed Google Chrome app (channel=chrome), not Playwright's
// bundled Chromium. This is native Chrome coverage, not Chromium-GOST.
export default defineConfig(baseConfig, {
  workers: 1,
  use: {
    ...devices["Desktop Chrome"],
    channel: "chrome",
    baseURL: "http://127.0.0.1:18765",
    screenshot: "only-on-failure",
    trace: "on-first-retry",
  },
});
