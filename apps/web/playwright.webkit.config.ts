import { defineConfig, devices } from "@playwright/test";
import baseConfig from "./playwright.config";

// Browser-engine regression coverage close to Safari; this is not a native
// Safari certification and does not replace a manual macOS/iOS check.
export default defineConfig(baseConfig, {
  use: {
    ...devices["Desktop Safari"],
    baseURL: "http://127.0.0.1:18766",
    screenshot: "only-on-failure",
    trace: "on-first-retry",
  },
});
