import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const buildInfo = { uiVersion: '2.2.0', revision: process.env.VITE_BUILD_SHA || process.env.GITHUB_SHA || 'local', builtAt: new Date().toISOString() };
const releaseManifest = { name: 'release-manifest', generateBundle() { this.emitFile({ type: 'asset', fileName: 'release.json', source: JSON.stringify(buildInfo, null, 2) }); } };

export default defineConfig({
  plugins: [react(), releaseManifest],
  define: { __BUILD_INFO__: JSON.stringify(buildInfo) },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom"],
          vendor: ["axios", "lucide-react"],
        },
      },
    },
  },
})
