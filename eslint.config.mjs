// eslint.config.mjs — flat config for ESLint 9 + typescript-eslint v8
import tseslint from "typescript-eslint";

export default tseslint.config(...tseslint.configs.strictTypeChecked, {
  languageOptions: {
    parserOptions: {
      projectService: true,
      tsconfigRootDir: import.meta.dirname,
    },
  },
  rules: {
    // Allow void operator to intentionally ignore floating promises
    // (e.g. `void loadChain()` in event handlers)
    "@typescript-eslint/no-floating-promises": ["error", { ignoreVoid: true }],
    // Template literal types in HTML strings require casting — permit it
    "@typescript-eslint/restrict-template-expressions": [
      "error",
      { allowNumber: true, allowNullish: false },
    ],
    // Non-null assertions are acceptable for document.getElementById() calls in
    // a browser script where the developer controls the HTML structure.
    "@typescript-eslint/no-non-null-assertion": "off",
  },
});
