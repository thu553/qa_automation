/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'custom-teal': '#E6FFFA',
        'custom-teal-hover': '#B7F7F0',
      },
    },
  },
  plugins: [],
}