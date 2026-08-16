import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
const apiProxyTarget = process.env.VITE_API_URL || "http://127.0.0.1:8000";
export default defineConfig({
  appType: "spa",
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": apiProxyTarget,
      "/health": apiProxyTarget,
      "/mock-authority": apiProxyTarget,
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: "./tests/setup.ts",
    include: ["tests/**/*.{test,spec}.{js,ts,jsx,tsx}"],
    exclude: [
      "browser-e2e/**",
      "browser-real-stack/**",
      "test-results/**",
      "artifacts/**",
      "dist/**",
      "coverage/**",
      "node_modules/**",
    ],
    pool: "forks",
    maxWorkers: 1,
    fileParallelism: false,
  },
});
