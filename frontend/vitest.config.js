import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Test-only config. Vitest prefers vitest.config.js over vite.config.js, so the
// server block in vite.config.js (which reads the repo-root .env — machine-
// dependent) never applies here.
export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.js"],
  },
});
