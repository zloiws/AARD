import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      // Proxy API requests to backend to avoid CORS during development
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        secure: false,
        ws: true,
      },
      // Proxy websocket endpoints (if mounted elsewhere)
      "/ws": {
        target: "ws://localhost:8000",
        ws: true,
        changeOrigin: true,
        secure: false,
      }
    }
  }
});


