import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  // ponytail: dev-only LAN access; drop allowedHosts when a reverse proxy fronts this.
  server: { host: '0.0.0.0', port: 5173, allowedHosts: true },
})
