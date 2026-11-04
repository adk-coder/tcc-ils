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

// ------------------------------------------------------------ estilo de aprendizagem (ILS)
export type Dimensao = 'ati_ref' | 'sen_int' | 'vis_ver' | 'seq_glo'

export interface PerguntaEstilo {
  item: number            // número do item no ILS (o aluno não vê)
  numero: number          // 1ª, 2ª, 3ª pergunta feita a este aluno
  enunciado: string
  alternativa_a: string
  alternativa_b: string
}

export interface DimensaoEstilo {
  dimensao: Dimensao
  polo: string            // ex.: "ativo"
  polo_oposto: string     // ex.: "reflexivo"
  confianca: number       // 0,5 a 1: chance de o ILS completo dar o mesmo polo
  n_questoes: number
}

export interface ItemRespondido {
  numero: number          // posição na sessão (1, 2...)
  item: number            // 1..44 no ILS
  dimensao: Dimensao
  enunciado: string
}

export interface EstadoEstilo {
  status: 'nao_iniciado' | 'em_andamento' | 'concluido'
  respondidas: number
  partes_concluidas: number
  pergunta: PerguntaEstilo | null
  resultado: DimensaoEstilo[] | null
  itens_respondidos: ItemRespondido[] | null  // só no resultado final
  concluido_em: string | null
  textos_provisorios: boolean
}

// ------------------------------------------------------------ acompanhamento
export interface DesempenhoExercicio {
  id: number
  numero: number
  enunciado: string
  responderam: number
  acerto_primeira: number | null          // 0 a 1; null = ninguém respondeu
  erro_comum: { alternativa: number; quantos: number } | null
}

export interface DesempenhoModulo {
  id: number
  titulo: string
  concluiram: number
  exercicios: DesempenhoExercicio[]
}

export interface DesempenhoSala {
  n_alunos: number
  total_exercicios: number
  acerto_primeira_medio: number | null
  modulos: DesempenhoModulo[]
  alunos: { id: number; nome: string; acertados: number; pontos: number; ultima_atividade: string | null }[]
}

export interface Continuar {
  sala_id: number
  sala_nome: string
  modulo_id: number
  modulo_titulo: string
  feitos: number
  total: number
}

// ------------------------------------------------------------ adesivos de conquista
export interface Adesivo {
  id: string
  titulo: string
  descricao: string      // como ganhar
  meta: number
  progresso: number      // 0..meta
  ganho: boolean
  ganho_em: string | null
}
