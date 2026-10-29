import { defineConfig, devices } from "@playwright/test";
/** Separate TZ-111 smoke; generic engines do NOT certify branded browsers. */
export default defineConfig({
  testDir: "./e2e", testMatch: "browser-compat.spec.ts", fullyParallel: false,
  retries: process.env.CI ? 1 : 0, workers: 1, timeout: 30_000,
  expect: {timeout: 10_000}, reporter: process.env.CI ? "github" : "list",
  projects: [
    {name:"chromium",use:{...devices["Desktop Chrome"]}},
    {name:"webkit",use:{...devices["Desktop Safari"]}},
    {name:"firefox",use:{...devices["Desktop Firefox"]}},
    {name:"google-chrome",use:{...devices["Desktop Chrome"],channel:"chrome"}},
  ],
  use: {baseURL:"http://127.0.0.1:18766",screenshot:"only-on-failure"},
  webServer: {command:"php -S 127.0.0.1:18766 -t out",
    url:"http://127.0.0.1:18766/",reuseExistingServer: !process.env.CI,timeout:20_000},
});
