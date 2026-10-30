<!-- Ranking da sala. Aluno vê os colegas só como "Primeiro S." (LGPD); o professor vê o nome completo. -->
<script setup lang="ts">
import type { LinhaRanking } from '~/utils/tipos'

const props = defineProps<{ salaId: number }>()
const api = useApi()
const { data: linhas, error } = await useAsyncData(`ranking-${props.salaId}`,
  () => api<LinhaRanking[]>(`/salas/${props.salaId}/ranking`), { default: () => [] })

const ninguemPontuou = computed(() => linhas.value.every(l => l.pontos === 0))
</script>

<template>
  <section class="folha p-5" aria-labelledby="titulo-ranking">
    <h2 id="titulo-ranking" class="mb-4 flex items-center gap-2 text-lg">
      <Icone nome="trofeu" class="text-caneta" /> Ranking
    </h2>

    <p v-if="error" class="text-sm text-tinta-suave">Não foi possível carregar o ranking.</p>
    <p v-else-if="!linhas.length" class="text-sm text-tinta-suave">Nenhum aluno na sala ainda.</p>

    <template v-else>
      <p v-if="ninguemPontuou" class="mb-3 text-sm text-tinta-suave">Ninguém pontuou ainda. Que tal ser o primeiro?</p>
      <ol class="flex flex-col gap-1">
        <li v-for="l in linhas" :key="l.posicao"
            class="flex items-center gap-3 rounded-lg px-2 py-1.5"
            :class="l.sou_eu && 'bg-marca/30'">
          <span class="w-6 shrink-0 text-center font-display font-extrabold"
                :class="l.posicao <= 3 && l.pontos > 0 ? 'text-caneta text-lg' : 'text-tinta-suave'">
            {{ l.posicao }}
          </span>
          <span class="flex min-w-0 flex-1 items-center gap-1.5">
            <span class="truncate" :class="l.sou_eu && 'font-medium'">{{ l.nome }}</span>
            <!-- fora do truncate: o "você" nunca é cortado -->
            <span v-if="l.sou_eu" class="shrink-0 rounded-full bg-white px-1.5 text-xs font-medium text-tinta-suave">você</span>
          </span>
          <span class="shrink-0 font-display font-semibold">{{ l.pontos }}</span>
        </li>
      </ol>
    </template>
  </section>
</template>
