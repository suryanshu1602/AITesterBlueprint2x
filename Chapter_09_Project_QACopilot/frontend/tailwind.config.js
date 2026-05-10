/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        accent: {
          DEFAULT: "#06b6d4",
          strong: "#0891b2",
          soft: "#cffafe",
        },
        ink: {
          DEFAULT: "#111827",
          soft: "#4b5563",
          muted: "#6b7280",
        },
        surface: {
          DEFAULT: "#ffffff",
          soft: "#fafafa",
          card: "#f3f4f6",
        },
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'Menlo', 'Monaco', 'monospace'],
      },
    },
  },
  plugins: [],
};
