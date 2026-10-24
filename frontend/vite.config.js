import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In dev (npm run dev) and preview (npm run preview) the app calls /api on its
// own origin and Vite forwards it to the backend. Set VITE_PROXY_TARGET to
// point at a backend elsewhere (docker compose uses http://backend:5000).
const apiProxy = {
  '/api': {
    target: process.env.VITE_PROXY_TARGET || 'http://localhost:5000',
    changeOrigin: true,
  },
}

export default defineConfig({
  plugins: [react()],
  server: { proxy: apiProxy },
  preview: { proxy: apiProxy },
  build: {
    rollupOptions: {
      output: {
        // Keep big libraries in their own cached chunks.
        manualChunks: {
          react: ['react', 'react-dom', 'react-router-dom'],
          charts: ['recharts'],
          graph: ['react-force-graph-2d'],
        },
      },
    },
  },
})
