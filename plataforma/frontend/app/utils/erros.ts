// Transforma erros da API (FastAPI) em mensagens claras para o usuário.

const CAMPOS: Record<string, string> = {
  nome: 'Informe seu nome (pelo menos 2 letras).',
  email: 'Confira o e-mail digitado.',
  senha: 'A senha precisa ter pelo menos 8 caracteres.',
  aceite_termos: 'Para criar a conta, aceite os termos de uso e a política de privacidade.',
  codigo: 'O código da sala tem 6 caracteres.',
}

export function mensagemDeErro(erro: unknown): string {
  const e = erro as { data?: { detail?: unknown }; response?: unknown }
  if (!e?.response) return 'Não foi possível falar com o servidor. Confira se a API está rodando.'
  const detalhe = e.data?.detail
  if (typeof detalhe === 'string') return detalhe.charAt(0).toUpperCase() + detalhe.slice(1) + '.'
  if (Array.isArray(detalhe) && detalhe.length) {
    // erros de validação: [{ loc: ['body', 'campo'], msg: '...' }]
    const campo = String(detalhe[0]?.loc?.at(-1) ?? '')
    return CAMPOS[campo] ?? 'Confira os dados e tente de novo.'
  }
  return 'Algo deu errado. Tente de novo.'
}
