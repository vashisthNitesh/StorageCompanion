import js from "@eslint/js";
import pluginVue from "eslint-plugin-vue";
import tseslint from "typescript-eslint";
import globals from "globals";

export default tseslint.config(
  { ignores: ["dist/**", "node_modules/**", "*.config.*"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...pluginVue.configs["flat/recommended"],
  {
    files: ["**/*.vue"],
    languageOptions: { parserOptions: { parser: tseslint.parser, extraFileExtensions: [".vue"] } },
  },
  {
    languageOptions: { globals: { ...globals.browser }, ecmaVersion: "latest", sourceType: "module" },
    rules: {
      // House rules: nothing raw reaches the user.
      "no-alert": "error",
      "no-console": "error",
      "vue/no-v-html": "error",
      "vue/no-restricted-html-elements": [
        "error",
        { element: "select", message: "Use UiSelect instead of a native <select>." },
      ],
      "@typescript-eslint/no-explicit-any": "off",
      "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
      "no-empty": ["error", { allowEmptyCatch: true }],
      "vue/multi-word-component-names": "off",
      "vue/max-attributes-per-line": "off",
      "vue/singleline-html-element-content-newline": "off",
      "vue/multiline-html-element-content-newline": "off",
      "vue/html-self-closing": "off",
      "vue/html-indent": "off",
      "vue/html-closing-bracket-newline": "off",
      "vue/attributes-order": "off",
      "vue/first-attribute-linebreak": "off",
      "vue/require-default-prop": "off",
    },
  },
  {
    files: ["src/lib/logger.ts"],
    rules: { "no-console": "off" },
  }
);
