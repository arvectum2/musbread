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
  use: {baseURL:"http://127.0.0.1:18765",screenshot:"only-on-failure"},
  webServer: {command:"python3 -m http.server 18765 --bind 127.0.0.1 --directory out",
    url:"http://127.0.0.1:18765/",reuseExistingServer: !process.env.CI,timeout:20_000},
});
