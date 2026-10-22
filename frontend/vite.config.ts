import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "path";

// Backend for the dev-server proxy; override with API_PROXY_TARGET if port 8000 is taken.
const apiTarget = process.env.API_PROXY_TARGET || "http://127.0.0.1:8000";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [vue()],
  // Production builds must never log to the browser console.
  esbuild: mode === "production" ? { drop: ["console", "debugger"] } : {},
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    host: "0.0.0.0",
    proxy: {
      "/api": {
        target: apiTarget,
        changeOrigin: true,
      },
      "/django-admin": {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
  worker: {
    format: "es",
  },
}));
