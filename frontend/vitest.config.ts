import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'happy-dom',
    setupFiles: ['./src/workbench/__tests__/setup.ts'],
    include: ['src/workbench/**/*.test.{ts,tsx}'],
  },
  resolve: {
    alias: {
      '@workbench': resolve(__dirname, 'src/workbench'),
    },
  },
});
