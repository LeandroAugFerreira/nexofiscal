import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({
  plugins: [react()],
  server: {port: 5180, strictPort: true, proxy: {'/api': {target: process.env.API_PROXY_TARGET || 'http://127.0.0.1:8010'}}},
  preview: {port: 5180, strictPort: true},
  build: {chunkSizeWarningLimit: 650, rollupOptions: {output: {manualChunks: {charts: ['recharts'], vendor: ['react', 'react-dom', 'react-router-dom']}}}},
});
