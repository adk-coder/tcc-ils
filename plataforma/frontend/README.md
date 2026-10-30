# MatIF — frontend (Nuxt 4)

```powershell
cd plataforma\frontend
npm install nuxt@^4 vue vue-router @nuxt/fonts
npm install -D tailwindcss @tailwindcss/vite
npm run dev          # http://localhost:3000  (a API precisa estar rodando em :8000)
```

Estrutura (Nuxt 4 coloca o código do app dentro de `app/`):

- `assets/css/main.css` — design system "caderno": cores, fontes, papel quadriculado, marca-texto
- `components/` — peças reutilizáveis (Botao, Campo, Aviso, Logo, CartaoSala, formulários)
- `composables/` — `useApi` (chamadas à API com o token), `useSessao` (login/cadastro/sair), `useToken`
- `middleware/auth.global.ts` — bloqueia páginas sem login
- `layouts/` — `default` (menu lateral / barra inferior) e `publico` (telas sem login)
- `pages/` — cada arquivo é uma rota (`salas/[id].vue` → `/salas/3`)
