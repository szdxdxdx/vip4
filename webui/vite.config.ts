import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue()],
  server: { proxy: { '/task': { target: 'http://127.0.0.1:8414', changeOrigin: true } } },
})
