// Token de acesso (JWT). Fica num cookie para sobreviver ao recarregar a página
// e num estado compartilhado para todos os componentes enxergarem o mesmo valor.

const NOME_COOKIE = 'matif_token'

export function useToken() {
  const cookie = useCookie<string | null>(NOME_COOKIE, {
    sameSite: 'lax',
    maxAge: 60 * 60, // mesma validade do token na API (60 min)
  })
  const token = useState<string | null>('token', () => cookie.value ?? null)

  function definir(valor: string | null) {
    token.value = valor
    cookie.value = valor
  }

  return { token, definir }
}
