/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: '#0a0f18',
        panel: '#111a28',
        panel2: '#162235',
        border: '#26364d',
        text: '#edf3fb',
        muted: '#9aaac0',
        green: '#35d07f',
        red: '#ff6376',
        amber: '#f7c66b',
        blue: '#70b7ff',
      },
    },
  },
  plugins: [],
}