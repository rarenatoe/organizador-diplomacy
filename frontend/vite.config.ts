import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import { resolve } from "path";

export default defineConfig({
  plugins: [svelte()],
  base: "/static/",
  root: "src",
  build: {
    outDir: resolve(__dirname, "static"),
    emptyOutDir: false,
    rollupOptions: {
      input: "index.html",
      output: {
        entryFileNames: "app.js",
        assetFileNames: "[name].[ext]",
      },
    },
  },
  server: {
    proxy: {
      "/api": "http://localhost:5001",
    },
  },
});
