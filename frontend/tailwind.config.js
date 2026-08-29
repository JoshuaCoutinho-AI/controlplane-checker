/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Every color below is backed by a CSS variable (see
        // src/index.css) so the whole palette flips between dark and
        // light instantly when ThemeToggle swaps the `.light` class on
        // <html> — no per-element dark: variants needed anywhere.
        ink: 'rgb(var(--c-ink) / <alpha-value>)',
        panel: 'rgb(var(--c-panel) / <alpha-value>)',
        panel2: 'rgb(var(--c-panel-2) / <alpha-value>)',
        hairline: 'rgb(var(--c-hairline) / <alpha-value>)',
        paper: 'rgb(var(--c-paper) / <alpha-value>)',
        muted: 'rgb(var(--c-muted) / <alpha-value>)',
        brass: {
          DEFAULT: 'rgb(var(--c-brass) / <alpha-value>)',
          soft: 'rgb(var(--c-brass-soft) / <alpha-value>)',
          dim: 'rgb(var(--c-brass-dim) / <alpha-value>)',
        },
        signal: {
          DEFAULT: 'rgb(var(--c-signal) / <alpha-value>)',
          soft: 'rgb(var(--c-signal-soft) / <alpha-value>)',
        },
        pass: {
          DEFAULT: 'rgb(var(--c-pass) / <alpha-value>)',
          soft: 'rgb(var(--c-pass-soft) / <alpha-value>)',
        },
        log: {
          DEFAULT: 'rgb(var(--c-log) / <alpha-value>)',
          soft: 'rgb(var(--c-log-soft) / <alpha-value>)',
        },
        block: {
          DEFAULT: 'rgb(var(--c-block) / <alpha-value>)',
          soft: 'rgb(var(--c-block-soft) / <alpha-value>)',
        },
      },
      fontFamily: {
        // A warm literary serif for the hero moment (in the spirit of
        // Claude's own display face), a clean grotesk for UI text set
        // larger than a dense dashboard would use, and monospace kept
        // strictly for numeric instrument readouts.
        display: ['"Fraunces"', 'ui-serif', 'Georgia', 'serif'],
        body: ['"Inter"', 'ui-sans-serif', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        hero: ['clamp(2.25rem, 4vw + 1rem, 3.5rem)', { lineHeight: '1.08', letterSpacing: '-0.01em' }],
      },
      boxShadow: {
        panel: '0 1px 0 0 rgb(255 255 255 / 0.03) inset, 0 12px 32px -16px rgb(0 0 0 / 0.5)',
        glow: '0 0 0 1px rgb(var(--c-brass) / 0.4), 0 0 28px -4px rgb(var(--c-brass) / 0.35)',
        float: '0 20px 50px -20px rgb(0 0 0 / 0.35)',
      },
      keyframes: {
        'fade-slide-up': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'pulse-dot': {
          '0%, 100%': { opacity: '1', boxShadow: '0 0 0 0 rgb(var(--c-pass) / 0.5)' },
          '50%': { opacity: '0.7', boxShadow: '0 0 0 4px rgb(var(--c-pass) / 0)' },
        },
      },
      animation: {
        'fade-slide-up': 'fade-slide-up 0.4s cubic-bezier(0.16, 1, 0.3, 1) both',
        'fade-in': 'fade-in 0.5s ease-out both',
        'pulse-dot': 'pulse-dot 2s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
