import { defineConfig } from "vitest/config";
import { svelte } from "@sveltejs/vite-plugin-svelte";

export default defineConfig({
  plugins: [svelte()],
  test: {
    environment: "jsdom",
    include: ["frontend/src/**/*.test.ts"],
    globals: true,
    setupFiles: ["frontend/test-setup.ts"],
    server: {
      deps: {
        inline: [/@testing-library\/svelte/],
      },
    },
    alias: {
      $app: "/frontend/src/app",
    },
  },
  resolve: {
    conditions: ["browser"],
  },
});
