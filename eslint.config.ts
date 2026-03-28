// eslint.config.ts — flat config for ESLint 10 + typescript-eslint v8
import { defineConfig } from "eslint/config";
import tseslint from "typescript-eslint";
import svelte from "eslint-plugin-svelte";
import vitest from "@vitest/eslint-plugin";

export default defineConfig([
  // TypeScript files configuration
  ...tseslint.configs.strictTypeChecked.map((config) => ({
    ...config,
    files: ["frontend/src/**/*.ts"],
  })),
  {
    files: ["frontend/src/**/*.ts"],
    plugins: {
      "@typescript-eslint": tseslint.plugin,
    },
    languageOptions: {
      parserOptions: {
        projectService: true,
      },
    },
    rules: {
      "@typescript-eslint/dot-notation": "error",
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/naming-convention": [
        "error",
        {
          selector: "default",
          format: ["camelCase"],
          leadingUnderscore: "allow",
        },
        {
          selector: "typeLike",
          format: ["PascalCase"],
        },
        {
          selector: "variable",
          format: ["camelCase", "UPPER_CASE", "PascalCase"],
        },
        {
          selector: "property",
          format: ["camelCase", "snake_case"],
          leadingUnderscore: "allow",
        },
        {
          selector: "parameter",
          format: ["camelCase", "PascalCase"],
          leadingUnderscore: "allow",
        },
        {
          // Svelte component imports use PascalCase (e.g. `import Header from './Header.svelte'`)
          selector: "import",
          format: ["camelCase", "PascalCase"],
        },
      ],
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
      // Allow void expressions in arrow function callbacks (e.g., `setTimeout(() => toast.remove(), 300)`)
      "@typescript-eslint/no-confusing-void-expression": [
        "error",
        { ignoreArrowShorthand: true },
      ],
    },
  },
  // Vitest test files configuration
  {
    files: ["frontend/src/**/*.test.ts", "frontend/test-setup.ts"],
    ...vitest.configs.recommended,
  },
  // Svelte files configuration with proper TypeScript support
  ...svelte.configs["flat/recommended"].map((config) => ({
    ...config,
    files: ["frontend/src/**/*.svelte"],
  })),
  {
    files: ["frontend/src/**/*.svelte"],
    plugins: {
      "@typescript-eslint": tseslint.plugin,
    },
    languageOptions: {
      parserOptions: {
        parser: tseslint.parser,
      },
    },
    rules: {
      "dot-notation": "error",
      // Disable TypeScript rules that require type information for Svelte files
      "@typescript-eslint/no-floating-promises": "off",
      "@typescript-eslint/restrict-template-expressions": "off",
      "@typescript-eslint/no-confusing-void-expression": "off",
      // The flat/recommended config already includes a11y rules
      // Additional custom rules can be added here if needed
    },
  },
]);
