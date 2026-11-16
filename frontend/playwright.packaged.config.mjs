import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: "**/packaged.spec.mjs",
  workers: 1,
  timeout: 60000,
  outputDir: "../deployment-results/browser",
  reporter: [
    ["list"],
    ["junit", { outputFile: "../deployment-results/packaged-browser.xml" }],
  ],
  use: {
    baseURL: process.env.PACKAGED_ORIGIN || "http://127.0.0.1:8080",
    // Only the disposable CI self-signed certificate is exempt here.
    // verify_compose.py separately validates its trust chain using a dedicated CA file.
    ignoreHTTPSErrors: process.env.PACKAGED_TEST_SELF_SIGNED === "1",
    screenshot: "only-on-failure",
  },
});
