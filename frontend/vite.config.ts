import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Get backend port from environment variable, default to 8008
const BACKEND_PORT = process.env.BACKEND_PORT || '8008'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: `http://localhost:${BACKEND_PORT}`,
        changeOrigin: true,
        secure: false,
      }
    }
  }
})
