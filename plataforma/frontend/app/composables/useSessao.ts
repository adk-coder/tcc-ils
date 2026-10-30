// Sessão do usuário: entrar, criar conta, sair e quem está logado.

export interface Usuario {
  id: number
  nome: string
  email: string
  perfil: 'professor' | 'aluno'
  criado_em: string
}

export interface DadosCadastro {
  nome: string
  email: string
  senha: string
  perfil: 'professor' | 'aluno'
  aceite_termos: boolean
}

export function useSessao() {
  const { token, definir } = useToken()
  const usuario = useState<Usuario | null>('usuario', () => null)
  const api = useApi()

  async function carregar() {
    usuario.value = token.value ? await api<Usuario>('/auth/eu') : null
    return usuario.value
  }

  async function entrar(email: string, senha: string) {
    const r = await api<{ access_token: string }>('/auth/login', { method: 'POST', body: { email, senha } })
    definir(r.access_token)
    await carregar()
  }

  async function cadastrar(dados: DadosCadastro) {
    await api('/auth/registrar', { method: 'POST', body: dados })
    await entrar(dados.email, dados.senha)
  }

  function sair() {
    definir(null)
    usuario.value = null
    clearNuxtData() // descarta dados carregados da conta anterior
    clearNuxtState(['adesivos-conhecidos', 'adesivo-novo'])
    return navigateTo('/entrar')
  }

  const ehProfessor = computed(() => usuario.value?.perfil === 'professor')
  const primeiroNome = computed(() => usuario.value?.nome.split(' ')[0] ?? '')

  return { usuario, carregar, entrar, cadastrar, sair, ehProfessor, primeiroNome }
}
