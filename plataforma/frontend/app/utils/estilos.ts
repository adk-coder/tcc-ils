// Textos de apoio do resultado do questionário de estilos (modelo de Felder e Silverman).
// Linguagem pensada para o 9º ano. Revisar com o orientador.
import type { Dimensao } from '~/utils/tipos'

export const DIMENSOES: Record<Dimensao, { pergunta: string; polos: [string, string] }> = {
  ati_ref: { pergunta: 'Como você processa o que aprende', polos: ['ativo', 'reflexivo'] },
  sen_int: { pergunta: 'Que tipo de informação você prefere', polos: ['sensorial', 'intuitivo'] },
  vis_ver: { pergunta: 'Como a informação entra melhor', polos: ['visual', 'verbal'] },
  seq_glo: { pergunta: 'Como você chega a entender', polos: ['sequencial', 'global'] },
}

// trecho: pedaço da frase-resumo "Você aprende bem ___, ___, ___ e ___."
export const POLOS: Record<string, { nome: string; trecho: string; descricao: string; dica: string; dica_outro_lado: string }> = {
  ativo: {
    nome: 'Ativo',
    trecho: 'colocando a mão na massa',
    descricao: 'Você tem preferência por aprender fazendo: testando, discutindo e explicando para alguém.',
    dica: 'Logo depois de ler o módulo, tente um exercício e explique a resolução em voz alta.',
    dica_outro_lado: 'Depois de praticar, pare alguns minutos para revisar o que fez e escrever com suas palavras o que aprendeu.',
  },
  reflexivo: {
    nome: 'Reflexivo',
    trecho: 'pensando com calma antes de fazer',
    descricao: 'Você tem preferência por pensar com calma antes de agir e organizar as ideias sozinho.',
    dica: 'Pare a cada parágrafo e escreva com suas palavras o que entendeu antes de seguir.',
    dica_outro_lado: 'Teste o que entendeu resolvendo exercícios logo depois de ler a explicação, mesmo antes de ter certeza.',
  },
  sensorial: {
    nome: 'Sensorial',
    trecho: 'com exemplos concretos',
    descricao: 'Você prefere fatos, exemplos concretos e procedimentos práticos.',
    dica: 'Comece pelos exemplos resolvidos e só depois volte para a regra geral.',
    dica_outro_lado: 'Depois de resolver alguns exercícios parecidos, tente descobrir a regra geral que vale para todos eles.',
  },
  intuitivo: {
    nome: 'Intuitivo',
    trecho: 'descobrindo ideias e padrões',
    descricao: 'Você prefere ideias, conceitos e descobrir relações e padrões.',
    dica: 'Procure o "porquê" de cada regra e confira com calma as contas, onde costuma escapar um detalhe.',
    dica_outro_lado: 'Confira cada passo das contas com atenção e refaça um exemplo concreto antes de passar para o próximo conteúdo.',
  },
  visual: {
    nome: 'Visual',
    trecho: 'vendo desenhos e esquemas',
    descricao: 'Você tem preferência por informações visuais: desenhos, esquemas, gráficos e cores.',
    dica: 'Transforme o problema num desenho: barras para frações, retas numéricas, tabelas.',
    dica_outro_lado: 'Explique por escrito, com suas palavras, o que um desenho ou esquema mostra.',
  },
  verbal: {
    nome: 'Verbal',
    trecho: 'lendo e ouvindo explicações',
    descricao: 'Você tem preferência por explicações escritas ou faladas.',
    dica: 'Resuma cada módulo em poucas frases e leia a explicação de cada exercício com atenção.',
    dica_outro_lado: 'Faça um desenho, uma tabela ou um esquema para representar o problema antes de resolvê-lo.',
  },
  sequencial: {
    nome: 'Sequencial',
    trecho: 'seguindo um passo de cada vez',
    descricao: 'Você tende a entender bem em passos lógicos, um depois do outro.',
    dica: 'Siga os módulos na ordem e resolva os exercícios do mais fácil para o mais difícil.',
    dica_outro_lado: 'Antes de começar um módulo, leia o texto inteiro para entender aonde ele quer chegar.',
  },
  global: {
    nome: 'Global',
    trecho: 'olhando primeiro o todo',
    descricao: 'Você tende a entender "de repente", quando enxerga o todo e as partes se encaixam.',
    dica: 'Antes de começar, dê uma olhada geral no módulo inteiro para ver aonde ele quer chegar.',
    dica_outro_lado: 'Depois de entender a ideia geral, resolva os exercícios na ordem, um passo de cada vez.',
  },
}

/** "Você aprende bem fazendo..., com exemplos..., vendo... e seguindo..." */
export function frasePerfil(polos: string[]): string {
  const t = polos.map(p => POLOS[p]?.trecho).filter(Boolean) as string[]
  if (t.length < 2) return t[0] ?? ''
  return `${t.slice(0, -1).join(', ')} e ${t.at(-1)}`
}
