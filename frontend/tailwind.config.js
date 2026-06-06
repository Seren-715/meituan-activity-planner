/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        meituan: {
          yellow: '#FFD100',
          'yellow-dark': '#F5C000',
          'yellow-light': '#FFF8E1',
          'yellow-hover': '#FFE44D',
          ink: '#1C1C1C',
          'ink-secondary': '#666666',
          'ink-muted': '#999999',
          canvas: '#FFFFFF',
          'canvas-warm': '#FFFDF5',
          'canvas-soft': '#F7F7F7',
          hairline: '#E8E8E8',
          'hairline-soft': '#F0F0F0',
          success: '#00B578',
          error: '#FF4D4F',
          orange: '#FF9900',
        },
      },
      fontFamily: {
        sans: [
          'PingFang SC', 'Microsoft YaHei', 'Hiragino Sans GB',
          '-apple-system', 'BlinkMacSystemFont', 'Segoe UI',
          'Roboto', 'Helvetica Neue', 'Arial', 'sans-serif',
        ],
      },
      borderRadius: {
        'pill': '9999px',
      },
      boxShadow: {
        'card': '0 2px 8px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)',
        'card-hover': '0 8px 24px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.04)',
        'card-elevated': '0 12px 32px rgba(255,209,0,0.10), 0 4px 8px rgba(0,0,0,0.04)',
        'button': '0 2px 4px rgba(255,209,0,0.3)',
      },
    },
  },
  plugins: [],
}
