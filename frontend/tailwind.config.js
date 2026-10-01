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
        cad: {
          bg: '#0a0e17',
          surface: '#101726',
          raised: '#172033',
          border: '#1e293b',
          'border-strong': '#334155',
          critical: '#dc2626',
          'critical-bg': '#450a0a',
          warning: '#d97706',
          'warning-bg': '#451a03',
          success: '#059669',
          'success-bg': '#022c22',
          info: '#0284c7',
          text: '#f8fafc',
          muted: '#94a3b8',
          dim: '#64748b'
        }
      },
      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          'Roboto',
          '"Helvetica Neue"',
          'Arial',
          'sans-serif'
        ],
        mono: [
          '"JetBrains Mono"',
          'ui-monospace',
          'SFMono-Regular',
          'Menlo',
          'Monaco',
          'Consolas',
          'monospace'
        ]
      }
    },
  },
  plugins: [],
}
