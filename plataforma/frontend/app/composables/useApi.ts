// Cliente da API: já coloca o endereço base e o token em toda requisição.
// Se a API responder 401 (token vencido ou inválido), encerra a sessão.

export function useApi() {
  const config = useRuntimeConfig()
  const { token, definir } = useToken()

  return $fetch.create({
    baseURL: config.public.apiBase as string,
    onRequest({ options }) {
      if (token.value) {
        const cabecalhos = new Headers(options.headers as HeadersInit | undefined)
        cabecalhos.set('Authorization', `Bearer ${token.value}`)
        options.headers = cabecalhos
      }
    },
    async onResponseError({ response }) {
      if (response.status === 401 && token.value) {
        definir(null)
        useState('usuario').value = null
        await navigateTo('/entrar')
      }
    },
  })
}
