// eslint.config.ts — flat config for ESLint 10 + typescript-eslint v8
import { defineConfig } from "eslint/config";
import tseslint from "typescript-eslint";

export default defineConfig([
  ...tseslint.configs.strictTypeChecked,
  {
    files: ["frontend/src/**/*.ts"],
    languageOptions: {
      parserOptions: {
        projectService: true,
      },
    },
    rules: {
      // Allow void operator to intentionally ignore floating promises
      // (e.g. `void loadChain()` in event handlers)
      "@typescript-eslint/no-floating-promises": [
        "error",
        { ignoreVoid: true },
      ],
      // Template literal types in HTML strings require casting — permit it
      "@typescript-eslint/restrict-template-expressions": [
        "error",
        { allowNumber: true, allowNullish: false },
      ],
      // Non-null assertions are acceptable for document.getElementById() calls in
      // a browser script where the developer controls the HTML structure.
      "@typescript-eslint/no-non-null-assertion": "off",
    },
  },
]);
