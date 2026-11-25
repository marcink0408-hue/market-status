/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: '#0e0d0d',
        panel: '#181414',
        panel2: '#211818',
        border: '#472321',
        text: '#ffffff',
        muted: '#b8b2b2',
        green: '#45e18c',
        red: '#ff5147',
        amber: '#ffd474',
        blue: '#388eff',
      },
    },
  },
  plugins: [],
}