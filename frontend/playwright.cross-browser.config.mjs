import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: "**/cross-browser.spec.mjs",
  workers: 1,
  timeout: 60000,
  outputDir: "test-results/cross-browser",
  reporter: [
    ["list"],
    ["junit", { outputFile: "test-results/cross-browser.xml" }],
  ],
  use: {
    baseURL: "http://127.0.0.1:5173",
    headless: true,
    screenshot: "only-on-failure",
  },
  projects: ["chromium", "firefox", "webkit"].map((browserName) => ({
    name: browserName,
    use: { browserName },
  })),
});
