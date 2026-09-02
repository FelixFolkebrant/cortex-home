import { Agent } from "node:http";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const coordinatorAgent = new Agent({ keepAlive: false });

export default defineConfig({
  build: {
    assetsInlineLimit: 0,
  },
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/api": {
        agent: coordinatorAgent,
        target: "http://127.0.0.1:8080",
      },
    },
  },
});
