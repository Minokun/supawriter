/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // 温暖色调配色方案
        primary: {
          DEFAULT: '#DC2626', // 红色
          light: '#F87171',     // 浅红
          dark: '#991B1B',      // 深红
        },
        cta: {
          DEFAULT: '#CA8A04',  // 琥珀色
          light: '#F59E0B',
          dark: '#92400E',
        },
        background: {
          DEFAULT: '#FEF2F2',  // 浅粉红背景
          dark: '#1F1515',
        },
        card: {
          DEFAULT: '#FFFFFF',  // 白色卡片
        },
        text: {
          primary: '#450A0A',  // 深红色文字
          secondary: '#7F1D1D', // 次要文字
          muted: '#991B1B',     // 暗淡文字
        },
        border: {
          DEFAULT: '#FECACA',  // 淡红边框
        },
      },
      fontFamily: {
        sans: ['Nunito', 'system-ui', 'sans-serif'],
        display: ['Fredoka', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        'sm': '6px',
        'md': '8px',
        'lg': '12px',
        'xl': '16px',
        '2xl': '20px',
      },
      boxShadow: {
        'sm': '0 1px 2px 0 rgb(0 0 0 / 0.05)',
        'md': '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
        'lg': '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
      },
      spacing: {
        '18': '4.5rem', // 72px
        '22': '5.5rem', // 88px
      },
    },
  },
  plugins: [],
}
