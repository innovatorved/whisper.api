import typography from "@tailwindcss/typography";

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./src/**/*.{astro,html,js,jsx,md,mdx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        "brand-primary": "#3F72AF",
        "brand-accent": "#00ADB5",
        "brand-dark": "#112D4E",
        "brand-light": "#EEEEEE",
        "brand-muted": "#393E46",
        "brand-soft": "#BBE1FA"
      },
      boxShadow: {
        "sm-glow": "0 2px 8px rgba(17, 45, 78, 0.08)",
        "md-glow": "0 4px 12px rgba(17, 45, 78, 0.1)"
      },
      transitionProperty: {
        "colors-transforms": "color, background-color, border-color, box-shadow, transform"
      }
    }
  },
  plugins: [typography]
};