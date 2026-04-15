/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["Archivo Black", "Impact", "sans-serif"],
        sans: ["DM Sans", "system-ui", "sans-serif"],
      },
      colors: {
        neon: { blue: "#00d4ff", pink: "#ff2d95", purple: "#a855f7" },
      },
      backgroundImage: {
        "flyer-gradient":
          "radial-gradient(ellipse at 20% 20%, rgba(168,85,247,0.45), transparent 50%), radial-gradient(ellipse at 80% 30%, rgba(255,45,149,0.35), transparent 45%), radial-gradient(ellipse at 50% 80%, rgba(0,212,255,0.25), transparent 50%), linear-gradient(165deg, #0f0c1a 0%, #1a0a2e 40%, #0d1b2a 100%)",
      },
    },
  },
  plugins: [],
};
