/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    container: { center: true, padding: "1rem" },
    extend: {
      fontFamily: { sans: ["Inter", "system-ui", "Segoe UI", "Roboto", "Arial"] },
      colors: {
        sisl: {
          bg: "#0f172a",        // sidebar bg (slate-900)
          panel: "#0b1220",     // sidebar panel
          primary: "#2563eb",   // blue-600
          accent: "#10b981",    // emerald-500
          ring: "#3b82f6"       // blue-500 focus ring
        }
      },
      borderRadius: {
        xl: "0.9rem",
        "2xl": "1.25rem"
      },
      boxShadow: {
        soft: "0 1px 2px rgba(16,24,40,0.06), 0 1px 3px rgba(16,24,40,0.10)",
        card: "0 2px 10px rgba(16,24,40,0.08)"
      },
      spacing: { 13: "3.25rem" },
    }
  },
  plugins: [],
};
