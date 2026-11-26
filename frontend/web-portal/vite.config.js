import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true,
    proxy: {
      '/api': {
        target: 'http://nginx',
        changeOrigin: true
      },
      '/artifacts': {
        target: 'http://nginx',
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://nginx',
        ws: true
      }
    }
  }
});
