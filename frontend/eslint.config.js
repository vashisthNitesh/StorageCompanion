// ESLint flat config (ESLint 9). `npm run lint` previously failed: no config and no eslint dependency.
import js from "@eslint/js";
import pluginVue from "eslint-plugin-vue";
import tseslint from "typescript-eslint";
import globals from "globals";

export default tseslint.config(
  { ignores: ["dist/**", "node_modules/**", "public/**", "*.tsbuildinfo"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...pluginVue.configs["flat/essential"],
  {
    files: ["**/*.{ts,vue}"],
    languageOptions: {
      globals: { ...globals.browser, ...globals.node },
      parserOptions: { parser: tseslint.parser, extraFileExtensions: [".vue"], sourceType: "module" },
    },
    rules: {
      // The codebase uses `any` at API boundaries; flag it in review rather than failing CI
      "@typescript-eslint/no-explicit-any": "off",
      "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_", varsIgnorePattern: "^_", caughtErrors: "none" }],
      "vue/multi-word-component-names": "off",
      "no-empty": ["error", { allowEmptyCatch: true }],
    },
  },
  {
    files: ["*.config.{js,ts}", "tailwind.config.js", "postcss.config.js"],
    languageOptions: { globals: globals.node },
  },
);
