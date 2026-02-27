import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { copyFileSync } from 'fs'

export default defineConfig({
  plugins: [
    react(),
    {
      name: 'copy-data-json',
      closeBundle() {
        // In the standalone website repo, data.json lives at the repo root.
        // Copy it into dist/ so Netlify serves it alongside the built assets.
        try {
          copyFileSync('data.json', 'dist/data.json')
          console.log('Copied data.json to dist/')
        } catch {
          console.warn('data.json not found at repo root, skipping copy')
        }
      }
    }
  ],
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
  },
})
