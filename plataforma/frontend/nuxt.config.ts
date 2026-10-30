// Configuração do frontend MatIF (Nuxt 4).
import tailwindcss from '@tailwindcss/vite'

export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',

  // SPA (sem renderização no servidor): tudo fica atrás de login, não há
  // necessidade de SEO, e o app fica mais simples de instalar como PWA.
  ssr: false,

  modules: ['@nuxt/fonts', '@vite-pwa/nuxt'],

  // @nuxt/fonts baixa as fontes e as serve pelo próprio app: o navegador do
  // aluno não faz requisição ao Google (minimização de dados — LGPD).
  fonts: {
    families: [
      { name: 'Lexend', provider: 'google', weights: [400, 500, 600] },
      { name: 'Bricolage Grotesque', provider: 'google', weights: [600, 800] },
    ],
  },

  css: ['~/assets/css/main.css'],
  vite: { plugins: [tailwindcss()] },

  // Endereço da API. Troque com a variável NUXT_PUBLIC_API_BASE.
  runtimeConfig: {
    public: { apiBase: 'http://localhost:8000' },
  },

  app: {
    head: {
      title: 'MatIF',
      htmlAttrs: { lang: 'pt-BR' },
      meta: [
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'description', content: 'Reforço de matemática para o Partiu IF' },
        { name: 'theme-color', content: '#2B59C3' },
      ],
      link: [
        { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' },
        { rel: 'apple-touch-icon', href: '/apple-touch-icon-180x180.png' },   // iPhone
      ],
    },
  },

  // PWA: o MatIF pode ser instalado no celular/computador como um aplicativo.
  // O "casco" do app (páginas, estilos, fontes, ícones) fica guardado no aparelho
  // e abre mesmo sem internet; os DADOS (exercícios, ranking, questionário) vêm
  // sempre da API, que fica em outro endereço e não é guardada (ver P11).
  pwa: {
    registerType: 'autoUpdate',            // nova versão publicada → atualiza sozinho
    manifest: {
      name: 'MatIF — Reforço de matemática',
      short_name: 'MatIF',
      description: 'Reforço de matemática para o Partiu IF',
      lang: 'pt-BR',
      start_url: '/',
      display: 'standalone',               // abre sem a barra do navegador
      background_color: '#F7F9FC',
      theme_color: '#2B59C3',
      icons: [
        { src: 'pwa-64x64.png', sizes: '64x64', type: 'image/png' },
        { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
        { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
        { src: 'maskable-icon-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
      ],
    },
    workbox: {
      navigateFallback: '/',               // SPA: qualquer rota abre o app
      globPatterns: ['**/*.{js,css,html,png,svg,ico,woff,woff2}'],
    },
    client: { installPrompt: true },       // guarda o convite de instalação para o botão da página Conta
    devOptions: { enabled: false },        // no "npm run dev" o PWA fica desligado; testar com build + preview
  },

  devtools: { enabled: false },
})
