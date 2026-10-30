// Gera os ícones do PWA (PNG em vários tamanhos) a partir de public/icone-app.svg.
// Rodar de novo só se o ícone mudar:  npx pwa-assets-generator
import { defineConfig, minimal2023Preset as preset } from '@vite-pwa/assets-generator/config'

export default defineConfig({
  preset,
  images: ['public/icone-app.svg'],
})
