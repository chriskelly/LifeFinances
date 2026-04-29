import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const apiProxyTarget =
  process.env.API_PROXY_TARGET ?? 'http://127.0.0.1:3501'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    /**
     * Bind IPv4 explicitly. `host: true` lets Node pick `::` first on some images; Docker Desktop’s
     * port publish path can then yield “empty reply” from the host while the app is healthy in-container.
     */
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    /** Dev only: accept any `Host:` (proxies / Docker sometimes send non-localhost names). */
    allowedHosts: true,
    proxy: {
      '/api': {
        target: apiProxyTarget,
        changeOrigin: true,
      },
    },
  },
})
