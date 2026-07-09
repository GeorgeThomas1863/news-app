import { fileURLToPath } from "node:url";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

const repoRoot = fileURLToPath(new URL("..", import.meta.url));

// FRONTEND_PORT / BACKEND_PORT come from the repo-root .env
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, repoRoot, "");
  return {
    plugins: [react()],
    server: {
      port: Number(env.FRONTEND_PORT) || 5173,
      proxy: {
        "/api": `http://localhost:${env.BACKEND_PORT || 8000}`,
      },
    },
  };
});
