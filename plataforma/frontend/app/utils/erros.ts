// Transforma erros da API (FastAPI) em mensagens claras para o usuário.

const CAMPOS: Record<string, string> = {
  nome: 'Informe o nome (pelo menos 2 letras).',
  email: 'Confira o e-mail digitado.',
  senha: 'A senha precisa ter pelo menos 8 caracteres.',
  aceite_termos: 'Para criar a conta, aceite os termos de uso e a política de privacidade.',
  codigo: 'O código da sala tem 6 caracteres.',
  titulo: 'O título precisa ter pelo menos 2 letras.',
  conteudo: 'O texto do módulo está grande demais.',
  enunciado: 'O enunciado precisa ter pelo menos 3 caracteres.',
  alternativas: 'O exercício precisa ter de 2 a 5 alternativas preenchidas.',
  pontos: 'Os pontos vão de 1 a 100.',
}

function capitalizar(t: string): string {
  return t.charAt(0).toUpperCase() + t.slice(1)
}

export function mensagemDeErro(erro: unknown): string {
  const e = erro as { data?: { detail?: unknown }; response?: unknown }
  if (!e?.response) return 'Não foi possível falar com o servidor. Confira se a API está rodando.'
  const detalhe = e.data?.detail
  if (typeof detalhe === 'string') return capitalizar(detalhe) + '.'
  if (Array.isArray(detalhe) && detalhe.length) {
    // erros de validação: [{ loc: ['body', 'campo'], msg: '...' }]
    const campo = String(detalhe[0]?.loc?.at(-1) ?? '')
    if (CAMPOS[campo]) return CAMPOS[campo]
    // validações do formulário inteiro (model_validator) já vêm em português
    const msg = String(detalhe[0]?.msg ?? '').replace(/^Value error, /, '')
    if (campo === 'body' && msg) return capitalizar(msg) + '.'
    return 'Confira os dados e tente de novo.'
  }
  return 'Algo deu errado. Tente de novo.'
}
