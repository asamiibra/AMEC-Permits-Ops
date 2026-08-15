import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
const apiProxyTarget = process.env.VITE_API_URL || "http://127.0.0.1:8000";
export default defineConfig({ appType: "spa", plugins: [react()], server: { port: 5173, proxy: { "/api": apiProxyTarget, "/health": apiProxyTarget, "/mock-authority": apiProxyTarget } }, test: { environment: "jsdom", setupFiles: "./tests/setup.ts", exclude: ["browser-e2e/**", "browser-real-stack/**", "node_modules/**"] } });
