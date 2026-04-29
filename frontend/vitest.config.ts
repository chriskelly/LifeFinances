import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

/** Vitest configuration for React component and interaction tests. */
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    environmentOptions: {
      jsdom: {
        url: 'http://localhost:5173/',
      },
    },
    setupFiles: ['./src/test/setup.ts'],
    /** Explicit `import { … } from 'vitest'` in test files; no injected globals. */
    globals: false,
    coverage: {
      provider: 'v8',
      reportsDirectory: './coverage',
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/main.tsx',
        'src/**/*.test.{ts,tsx}',
        'src/test/**',
        'src/types/**',
      ],
    },
  },
})
