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
      // strictPort: a silent bump lands on the backend's port and breaks the proxy;
      // 127.0.0.1: uvicorn binds IPv4 only, and localhost can resolve to ::1 first
      strictPort: true,
      proxy: {
        "/api": `http://127.0.0.1:${env.BACKEND_PORT || 8000}`,
      },
    },
  };
});
