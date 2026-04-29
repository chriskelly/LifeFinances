import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
// Default matches local dev (Vite and Flask on the host). Override in Docker, e.g.
// API_PROXY_TARGET=http://backend:3500
const apiProxyTarget = process.env.API_PROXY_TARGET ?? 'http://localhost:3500'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: apiProxyTarget,
        changeOrigin: true,
      },
    },
  },
})
