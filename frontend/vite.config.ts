import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import { resolve } from "path";
import dotenv from "dotenv";

// Manually load the root .env file into Node's process.env
dotenv.config({ path: resolve(__dirname, "../.env") });

export default defineConfig({
  plugins: [svelte()],
  base: "/static/",
  root: "src",
  build: {
    outDir: resolve(__dirname, "static"),
    emptyOutDir: false,
    rollupOptions: {
      input: resolve(__dirname, "src/index.html"),
      output: {
        entryFileNames: "app.js",
        assetFileNames: "[name].[ext]",
      },
    },
  },
  server: {
    proxy: {
      "/api": `http://127.0.0.1:${process.env.API_PORT || "5000"}`,
    },
  },
});
