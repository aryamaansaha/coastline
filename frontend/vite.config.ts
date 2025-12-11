import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Read backend port; default to 8008
const BACKEND_PORT = process.env.BACKEND_PORT || '8008'
// Read frontend HMR host from env, default to 'localhost'
const LAN_IP = process.env.LAN_IP || 'localhost'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,          // listen on 0.0.0.0 so other devices can connect
    port: 5173,
    strictPort: true,
    // HMR host now configurable via env var LAN_IP
    hmr: { host: LAN_IP },
    proxy: {
      '/api': {
        target: `http://localhost:${BACKEND_PORT}`,
        changeOrigin: true,
        secure: false,
      },
    },
  },
})