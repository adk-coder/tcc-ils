// Textos de apoio do resultado do questionário de estilos (modelo de Felder e Silverman).
// Linguagem pensada para o 9º ano. Revisar com o orientador.
import type { Dimensao } from '~/utils/tipos'

export const DIMENSOES: Record<Dimensao, { pergunta: string; polos: [string, string] }> = {
  ati_ref: { pergunta: 'Como você processa o que aprende', polos: ['ativo', 'reflexivo'] },
  sen_int: { pergunta: 'Que tipo de informação você prefere', polos: ['sensorial', 'intuitivo'] },
  vis_ver: { pergunta: 'Como a informação entra melhor', polos: ['visual', 'verbal'] },
  seq_glo: { pergunta: 'Como você chega a entender', polos: ['sequencial', 'global'] },
}

export const POLOS: Record<string, { nome: string; descricao: string; dica: string }> = {
  ativo: {
    nome: 'Ativo',
    descricao: 'Você aprende melhor fazendo: testando, discutindo e explicando para alguém.',
    dica: 'Logo depois de ler o módulo, tente um exercício e explique a resolução em voz alta.',
  },
  reflexivo: {
    nome: 'Reflexivo',
    descricao: 'Você aprende melhor pensando com calma antes de agir, organizando as ideias sozinho.',
    dica: 'Pare a cada parágrafo e escreva com suas palavras o que entendeu antes de seguir.',
  },
  sensorial: {
    nome: 'Sensorial',
    descricao: 'Você prefere fatos, exemplos concretos e procedimentos práticos.',
    dica: 'Comece pelos exemplos resolvidos e só depois volte para a regra geral.',
  },
  intuitivo: {
    nome: 'Intuitivo',
    descricao: 'Você prefere ideias, conceitos e descobrir relações e padrões.',
    dica: 'Procure o "porquê" de cada regra e confira com calma as contas, onde costuma escapar um detalhe.',
  },
  visual: {
    nome: 'Visual',
    descricao: 'Você lembra melhor do que vê: desenhos, esquemas, gráficos e cores.',
    dica: 'Transforme o problema num desenho: barras para frações, retas numéricas, tabelas.',
  },
  verbal: {
    nome: 'Verbal',
    descricao: 'Você lembra melhor das palavras: explicações escritas ou faladas.',
    dica: 'Resuma cada módulo em poucas frases e leia a explicação de cada exercício com atenção.',
  },
  sequencial: {
    nome: 'Sequencial',
    descricao: 'Você entende em passos lógicos, um depois do outro.',
    dica: 'Siga os módulos na ordem e resolva os exercícios do mais fácil para o mais difícil.',
  },
  global: {
    nome: 'Global',
    descricao: 'Você entende "de repente", quando enxerga o todo e as partes se encaixam.',
    dica: 'Antes de começar, dê uma olhada geral no módulo inteiro para ver aonde ele quer chegar.',
  },
}
