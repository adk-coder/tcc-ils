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

// ------------------------------------------------------------ conteúdo
export interface ModuloResumo {
  id: number
  titulo: string
  ordem: number
  n_exercicios: number
  n_acertados: number | null   // só para aluno
}

/** Exercício como o ALUNO recebe: sem a resposta certa e sem a explicação. */
export interface ExercicioAluno {
  id: number
  enunciado: string
  alternativas: string[]
  pontos: number
  ordem: number
  ja_respondeu: boolean
  ja_acertou: boolean
}

/** Exercício como o PROFESSOR recebe: completo. */
export interface ExercicioProfessor {
  id: number
  modulo_id: number
  enunciado: string
  alternativas: string[]
  indice_correta: number
  explicacao: string
  pontos: number
  ordem: number
}

export interface ModuloDetalhe {
  id: number
  sala_id: number
  titulo: string
  conteudo: string
  ordem: number
  exercicios: (ExercicioAluno | ExercicioProfessor)[]
}

export interface RespostaSaida {
  correta: boolean
  indice_correta: number
  explicacao: string
  pontos_ganhos: number
  primeira_tentativa: boolean
}

// ------------------------------------------------------------ gamificação
export interface LinhaRanking {
  posicao: number
  aluno_id: number | null   // só o professor recebe
  nome: string              // aluno vê só "Primeiro S." dos colegas
  pontos: number
  sou_eu: boolean
}

/** Letra da alternativa: 0 → A, 1 → B... */
export function letra(i: number): string {
  return String.fromCharCode(65 + i)
}
