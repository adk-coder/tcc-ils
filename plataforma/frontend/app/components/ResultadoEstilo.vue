<!-- Resultado do questionário: uma folha por dimensão, com o polo preferido em marca-texto,
     o que ele significa e uma dica de estudo ligada à plataforma. -->
<script setup lang="ts">
import type { DimensaoEstilo } from '~/utils/tipos'
import { DIMENSOES, POLOS } from '~/utils/estilos'

defineProps<{ resultado: DimensaoEstilo[] }>()

function porcentagem(x: number) {
  return `${Math.round(100 * x)}%`
}
</script>

<template>
  <div class="grid gap-4 sm:grid-cols-2">
    <article v-for="d in resultado" :key="d.dimensao" class="folha flex flex-col p-5 sm:p-6">
      <p class="text-sm text-tinta-suave">{{ DIMENSOES[d.dimensao].pergunta }}</p>

      <!-- os dois polos sempre na mesma ordem; o seu fica destacado -->
      <p class="mt-2 flex flex-wrap items-baseline gap-x-2 font-display">
        <template v-for="(polo, i) in DIMENSOES[d.dimensao].polos" :key="polo">
          <span v-if="i === 1" class="text-tinta-suave/50" aria-hidden="true">·</span>
          <span v-if="polo === d.polo" class="text-2xl font-extrabold text-tinta">
            <span class="marca-texto">{{ POLOS[polo]?.nome }}</span>
          </span>
          <span v-else class="text-lg font-semibold text-tinta-suave/60">{{ POLOS[polo]?.nome }}</span>
        </template>
      </p>

      <p class="mt-3">{{ POLOS[d.polo]?.descricao }}</p>
      <p class="mt-3 rounded-lg border-l-4 border-caneta bg-caneta/5 px-3 py-2 text-sm">
        <strong class="text-caneta">Dica de estudo:</strong> {{ POLOS[d.polo]?.dica }}
      </p>
      <p class="mt-auto pt-4 text-xs text-tinta-suave">
        Certeza da IA: {{ porcentagem(d.confianca) }} · {{ d.n_questoes }} {{ d.n_questoes === 1 ? 'pergunta' : 'perguntas' }}
      </p>
    </article>
  </div>
</template>
