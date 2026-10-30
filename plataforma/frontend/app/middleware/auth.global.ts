// Protege as páginas: sem login, só as rotas públicas abrem.
const PUBLICAS = ['/entrar', '/cadastro', '/privacidade']

export default defineNuxtRouteMiddleware(async (to) => {
  const { token, definir } = useToken()
  const sessao = useSessao()
  const publica = PUBLICAS.includes(to.path)

  if (!token.value) return publica ? undefined : navigateTo('/entrar')

  if (!sessao.usuario.value) {
    try {
      await sessao.carregar()
    } catch {
      definir(null) // token inválido ou API fora do ar
      return publica ? undefined : navigateTo('/entrar')
    }
  }

  // já logado não precisa ver as telas de entrar/cadastro
  if (to.path === '/entrar' || to.path === '/cadastro') return navigateTo('/')
})
