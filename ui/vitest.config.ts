import { defineConfig } from 'vitest/config'

export default defineConfig({
  esbuild: {
    jsx: 'automatic',
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./vitest.setup.ts'],
    deps: {
      optimizer: {
        web: {
          include: ['recharts'],
        },
      },
    },
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'json'],
      include: ['components/**/*.tsx', 'app/**/*.tsx'],
      exclude: ['node_modules', 'tests'],
    },
  },
})
