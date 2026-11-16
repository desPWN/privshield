/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        canvas: {
          DEFAULT: '#151518',
          elevated: '#1C1C20',
          subtle: '#1C1C20',
        },
        surface: {
          sidebar: '#1C1C20',
          panel: '#1E1E23',
          elevated: '#28282F',
          hover: '#32323B',
          border: 'rgba(255, 255, 255, 0.08)',
          'border-focus': 'rgba(229, 160, 13, 0.4)',
        },
        text: {
          primary: '#F2F2F7',
          secondary: '#A0A0A8',
          muted: '#6E6E78',
        },
        accent: {
          DEFAULT: '#E5A00D',
          hover: '#F5AE18',
          active: '#D49208',
          subtle: 'rgba(229, 160, 13, 0.12)',
          border: 'rgba(229, 160, 13, 0.25)',
        },
        success: {
          DEFAULT: '#32D74B',
          subtle: 'rgba(50, 215, 75, 0.12)',
          border: 'rgba(50, 215, 75, 0.25)',
        },
        warning: {
          DEFAULT: '#FF9F0A',
          subtle: 'rgba(255, 159, 10, 0.12)',
          border: 'rgba(255, 159, 10, 0.25)',
        },
        danger: {
          DEFAULT: '#FF453A',
          subtle: 'rgba(255, 69, 58, 0.12)',
          border: 'rgba(255, 69, 58, 0.25)',
        },
        info: {
          DEFAULT: '#0A84FF',
          subtle: 'rgba(10, 132, 255, 0.12)',
          border: 'rgba(10, 132, 255, 0.25)',
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          '"SF Pro Display"',
          'system-ui',
          'sans-serif',
        ],
        mono: [
          '"JetBrains Mono"',
          'ui-monospace',
          'SFMono-Regular',
          'Menlo',
          'monospace',
        ],
      },
      boxShadow: {
        'apple-sm': '0 1px 2px rgba(0, 0, 0, 0.3)',
        'apple-card': '0 1px 3px rgba(0, 0, 0, 0.4), 0 8px 24px rgba(0, 0, 0, 0.35)',
        'apple-elevated': '0 2px 8px rgba(0, 0, 0, 0.5), 0 16px 36px rgba(0, 0, 0, 0.45)',
        'apple-modal': '0 8px 32px rgba(0, 0, 0, 0.75), 0 0 0 1px rgba(255, 255, 255, 0.1)',
        'subtle-border': '0 0 0 1px rgba(255, 255, 255, 0.08)',
      },
      transitionTimingFunction: {
        'apple-spring': 'cubic-bezier(0.16, 1, 0.3, 1)',
      },
    },
  },
  plugins: [],
};