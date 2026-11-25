import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    // Mirrors the nginx /api reverse proxy so the browser always talks to one origin.
    proxy: { "/api": "http://localhost:5000" },
  },
});
