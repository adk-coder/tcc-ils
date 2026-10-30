// Formatos das respostas da API (espelham app/esquemas.py do backend).

export interface Sala {
  id: number
  nome: string
  codigo: string          // vazio para alunos
  professor_id: number
  criada_em: string
  n_alunos: number
}

export interface SalaDetalhe extends Sala {
  professor_nome: string
  alunos: { id: number; nome: string; entrou_em: string }[]   // só para o professor
}

export interface Progresso {
  pontos: number
  exercicios_acertados: number
  tentativas: number
  streak_atual: number
  melhor_streak: number
}
