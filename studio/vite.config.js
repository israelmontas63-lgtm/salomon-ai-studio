import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// API relativa por defecto (mismo origen en Render). No hardcodear localhost.
export default defineConfig({
  plugins: [react()],
  envPrefix: 'VITE_',
  define: {
    // Garantiza string vacío si no hay VITE_API_URL → fetch('/api/...')
    'import.meta.env.VITE_API_URL': JSON.stringify(process.env.VITE_API_URL || ''),
  },
})
