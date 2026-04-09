/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#DC2626',
          light: '#F87171',
          dark: '#991B1B',
        },
        cta: {
          DEFAULT: '#CA8A04',
        },
        background: {
          DEFAULT: '#FEF2F2',
        },
        text: {
          primary: '#450A0A',
          secondary: '#7F1D1D',
          muted: '#A8A29E',
        },
        border: '#E7E5E4',
        card: '#FFFFFF',
      },
      fontFamily: {
        sans: ['Nunito', 'sans-serif'],
        display: ['Fredoka', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
