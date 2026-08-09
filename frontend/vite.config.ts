import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({ plugins: [react()], server: { port: 5173, proxy: { "/api": "http://127.0.0.1:8000", "/health": "http://127.0.0.1:8000", "/mock-authority": "http://127.0.0.1:8000" } }, test: { environment: "jsdom", setupFiles: "./tests/setup.ts", exclude: ["browser-e2e/**", "browser-real-stack/**", "node_modules/**"] } });
