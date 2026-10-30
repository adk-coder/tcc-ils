<!-- Painel do professor: como a turma está indo numa sala.
     1. resumo (alunos, exercícios, acerto de primeira);
     2. exercícios que a turma mais erra, com a alternativa errada mais marcada;
     3. cada módulo: quantos concluíram e o acerto de cada exercício;
     4. cada aluno: exercícios certos, pontos e última atividade.
     "Acerto de primeira" = a 1ª resposta de cada aluno (antes de ver a correção). -->
<script setup lang="ts">
import { letra, type DesempenhoExercicio, type DesempenhoSala, type SalaDetalhe } from '~/utils/tipos'

const route = useRoute()
const api = useApi()
const sessao = useSessao()
const id = Number(route.params.id)
if (!sessao.ehProfessor.value) await navigateTo('/')

const { data: sala } = await useAsyncData(`sala-${id}`, () => api<SalaDetalhe>(`/salas/${id}`))
const { data: d, error } = await useAsyncData(`desempenho-${id}`, () => api<DesempenhoSala>(`/salas/${id}/desempenho`))
useHead({ title: () => `Desempenho — ${sala.value?.nome ?? 'Sala'} — MatIF` })

function pct(x: number | null | undefined) {
  return x == null ? '—' : `${Math.round(100 * x)}%`
}
// cor da barra: vermelho < 50%, amarelo < 75%, verde a partir de 75%
function corAcerto(x: number | null) {
  if (x == null) return 'bg-linha'
  return x < 0.5 ? 'bg-erro' : x < 0.75 ? 'bg-marca' : 'bg-acerto'
}

// exercícios mais difíceis: menor acerto de primeira entre os que alguém respondeu
const maisErrados = computed(() => {
  const todos: (DesempenhoExercicio & { modulo: string })[] = []
  for (const m of d.value?.modulos ?? []) for (const e of m.exercicios) todos.push({ ...e, modulo: m.titulo })
  return todos.filter(e => e.acerto_primeira != null && e.acerto_primeira < 1)
    .sort((a, b) => (a.acerto_primeira! - b.acerto_primeira!) || (b.responderam - a.responderam))
    .slice(0, 5)
})

// dias desde a última resposta (a API manda UTC; o SQLite às vezes perde o "Z")
function diasDesde(iso: string | null): number | null {
  if (!iso) return null
  const utc = /Z|[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`
  return Math.max(0, Math.floor((Date.now() - new Date(utc).getTime()) / 86_400_000))
}
function quando(iso: string | null) {
  const dias = diasDesde(iso)
  if (dias === null) return 'nunca respondeu'
  return dias === 0 ? 'hoje' : dias === 1 ? 'ontem' : `há ${dias} dias`
}
function parado(iso: string | null) {
  const dias = diasDesde(iso)
  return dias === null || dias >= 7
}
</script>

<template>
  <div class="flex flex-col gap-8">
    <LinkVoltar :para="`/salas/${id}`">Voltar para a sala</LinkVoltar>

    <header>
      <p class="text-sm font-medium uppercase tracking-wide text-caneta">Desempenho da turma</p>
      <h1 class="text-3xl md:text-4xl">{{ sala?.nome }}</h1>
    </header>

    <Aviso v-if="error">Não foi possível carregar o desempenho desta sala.</Aviso>

    <template v-else-if="d">
      <!-- 1. resumo -->
      <section class="folha grid grid-cols-3 divide-x divide-linha" aria-label="Resumo">
        <div class="p-4 text-center sm:p-5">
          <p class="font-display text-3xl font-extrabold">{{ d.n_alunos }}</p>
          <p class="mt-1 text-sm text-tinta-suave">{{ d.n_alunos === 1 ? 'aluno' : 'alunos' }}</p>
        </div>
        <div class="p-4 text-center sm:p-5">
          <p class="font-display text-3xl font-extrabold">{{ d.total_exercicios }}</p>
          <p class="mt-1 text-sm text-tinta-suave">exercícios</p>
        </div>
        <div class="p-4 text-center sm:p-5">
          <p class="font-display text-3xl font-extrabold"><span class="marca-texto">{{ pct(d.acerto_primeira_medio) }}</span></p>
          <p class="mt-1 text-sm text-tinta-suave">acerto de primeira</p>
        </div>
      </section>

      <p v-if="!d.n_alunos" class="folha p-5 text-tinta-suave">Nenhum aluno na sala ainda. Passe o código de convite para a turma.</p>
      <p v-else-if="d.acerto_primeira_medio == null" class="folha p-5 text-tinta-suave">
        Ninguém respondeu exercícios ainda. Os números aparecem aqui assim que a turma começar.
      </p>

      <!-- 2. o que revisar -->
      <section v-if="maisErrados.length" class="flex flex-col gap-3" aria-labelledby="titulo-revisar">
        <h2 id="titulo-revisar" class="text-xl">O que vale a pena revisar</h2>
        <ol class="flex flex-col gap-3">
          <li v-for="e in maisErrados" :key="e.id" class="folha flex flex-col gap-2 p-5">
            <p class="text-sm text-tinta-suave">{{ e.modulo }} · Exercício {{ e.numero }}</p>
            <p>{{ e.enunciado }}</p>
            <div class="flex items-center gap-3">
              <span class="h-2 flex-1 overflow-hidden rounded-full bg-linha">
                <span class="block h-full rounded-full" :class="corAcerto(e.acerto_primeira)"
                      :style="{ width: pct(e.acerto_primeira) }" />
              </span>
              <span class="shrink-0 text-sm"><strong>{{ pct(e.acerto_primeira) }}</strong> acertaram de primeira</span>
            </div>
            <p v-if="e.erro_comum" class="text-sm">
              Erro mais comum: alternativa <strong class="font-display">{{ letra(e.erro_comum.alternativa) }}</strong>
              ({{ e.erro_comum.quantos }} {{ e.erro_comum.quantos === 1 ? 'aluno' : 'alunos' }})
            </p>
          </li>
        </ol>
      </section>

      <!-- 3. por módulo -->
      <section v-if="d.modulos.length" class="flex flex-col gap-3" aria-labelledby="titulo-modulos">
        <h2 id="titulo-modulos" class="text-xl">Por módulo</h2>
        <article v-for="m in d.modulos" :key="m.id" class="folha p-5">
          <header class="mb-3 flex flex-wrap items-baseline justify-between gap-2">
            <NuxtLink :to="`/modulos/${m.id}`" class="font-display text-lg font-semibold text-tinta">{{ m.titulo }}</NuxtLink>
            <span class="text-sm text-tinta-suave">{{ m.concluiram }} de {{ d.n_alunos }} concluíram</span>
          </header>
          <p v-if="!m.exercicios.length" class="text-sm text-tinta-suave">Sem exercícios.</p>
          <ul v-else class="flex flex-col gap-2">
            <li v-for="e in m.exercicios" :key="e.id" class="grid grid-cols-[5.5rem_1fr_auto] items-center gap-3 text-sm">
              <span class="text-tinta-suave">Exercício {{ e.numero }}</span>
              <span class="h-2 overflow-hidden rounded-full bg-linha">
                <span class="block h-full rounded-full" :class="corAcerto(e.acerto_primeira)"
                      :style="{ width: e.acerto_primeira == null ? '0%' : pct(e.acerto_primeira) }" />
              </span>
              <span class="w-28 text-right">
                {{ e.acerto_primeira == null ? 'sem respostas' : `${pct(e.acerto_primeira)} · ${e.responderam} resp.` }}
              </span>
            </li>
          </ul>
        </article>
      </section>

      <!-- 4. por aluno -->
      <section v-if="d.alunos.length" class="flex flex-col gap-3" aria-labelledby="titulo-alunos">
        <h2 id="titulo-alunos" class="text-xl">Por aluno</h2>
        <div class="folha overflow-x-auto">
          <table class="w-full min-w-[28rem] text-left text-sm">
            <thead class="text-tinta-suave">
              <tr>
                <th class="px-5 py-3 font-normal">Aluno</th>
                <th class="px-3 py-3 font-normal">Certos</th>
                <th class="px-3 py-3 font-normal">Pontos</th>
                <th class="px-5 py-3 font-normal">Última atividade</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="a in d.alunos" :key="a.id" class="border-t border-linha">
                <td class="px-5 py-2.5">{{ a.nome }}</td>
                <td class="px-3 py-2.5">{{ a.acertados }}/{{ d.total_exercicios }}</td>
                <td class="px-3 py-2.5">{{ a.pontos }}</td>
                <td class="px-5 py-2.5" :class="parado(a.ultima_atividade) && 'text-erro'">{{ quando(a.ultima_atividade) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="text-xs text-tinta-suave">Em vermelho: sem responder há 7 dias ou mais.</p>
      </section>
    </template>
  </div>
</template>
