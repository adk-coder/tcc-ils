// Configuração do frontend MatIF (Nuxt 4).
import tailwindcss from '@tailwindcss/vite'

export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',

  // SPA (sem renderização no servidor): tudo fica atrás de login, não há
  // necessidade de SEO, e o app fica mais simples de instalar como PWA.
  ssr: false,

  modules: ['@nuxt/fonts'],

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
      link: [{ rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' }],
    },
  },

  devtools: { enabled: false },
})
