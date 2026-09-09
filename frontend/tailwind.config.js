/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        surface: {
          ground: "#F8FAFC",      // Soft, luminous slate-50 canvas
          card: "#FFFFFF",        // Pure crisp white card surface
          elevated: "#F1F5F9",    // Soft slate-100 hover / active wells
          subtle: "#E2E8F0",      // Slate-200 dividers, borders & pills
          border: "#E2E8F0",      // Refined light border
          borderHover: "#CBD5E1", // Slate-300 border hover
        },
        brand: {
          50: "#EFF6FF",
          100: "#DBEAFE",
          200: "#BFDBFE",
          300: "#93C5FD",
          400: "#60A5FA",
          500: "#3B82F6",
          600: "#2563EB",         // Royal Sapphire Blue
          700: "#1D4ED8",
          800: "#1E40AF",
          900: "#1E3A8A",
          950: "#172554",
        },
        accent: {
          orange: "#F97316",
          amber: "#D97706",
          emerald: "#059669",
          indigo: "#4F46E5",
          rose: "#E11D48",
        },
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["JetBrains Mono", "SFMono-Regular", "Menlo", "Monaco", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
}
