import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Same proxy target used for both `vite dev` and `vite preview` — Vite
// keeps these as separate config sections even though they're usually
// identical, so both are defined here to avoid one silently working
// while the other doesn't.
const apiProxy = {
  '/api': {
    target: 'http://backend:8000',
    changeOrigin: true,
    ws: true,
    rewrite: (path: string) => path.replace(/^\/api/, ''),
  },
}

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: apiProxy,
  },
  preview: {
    host: '0.0.0.0',
    port: 5173,
    proxy: apiProxy,
  },
})
