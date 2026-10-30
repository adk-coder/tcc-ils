<!-- Lista de módulos da sala. Aluno vê o quanto já acertou; professor vê quantos exercícios há. -->
<script setup lang="ts">
import type { ModuloResumo } from '~/utils/tipos'

defineProps<{ modulos: ModuloResumo[]; professor: boolean }>()

function porcentagem(m: ModuloResumo) {
  return m.n_exercicios ? Math.round(100 * (m.n_acertados ?? 0) / m.n_exercicios) : 0
}
function concluido(m: ModuloResumo) {
  return m.n_exercicios > 0 && (m.n_acertados ?? 0) >= m.n_exercicios
}
</script>

<template>
  <ol class="flex flex-col gap-3">
    <li v-for="(m, i) in modulos" :key="m.id">
      <NuxtLink :to="`/modulos/${m.id}`"
                class="folha flex items-center gap-4 p-4 text-tinta no-underline transition-colors hover:border-caneta sm:p-5">
        <!-- número do módulo; vira um "certo" quando o aluno conclui -->
        <span class="grid size-10 shrink-0 place-items-center rounded-full font-display text-lg font-extrabold"
              :class="!professor && concluido(m) ? 'bg-acerto text-white' : 'bg-caneta/10 text-caneta'">
          <Icone v-if="!professor && concluido(m)" nome="certo" />
          <template v-else>{{ i + 1 }}</template>
        </span>

        <span class="min-w-0 flex-1">
          <span class="block truncate font-display text-lg font-semibold">{{ m.titulo }}</span>
          <span v-if="professor" class="text-sm text-tinta-suave">
            {{ m.n_exercicios }} {{ m.n_exercicios === 1 ? 'exercício' : 'exercícios' }}
          </span>
          <span v-else-if="m.n_exercicios" class="mt-1.5 flex items-center gap-3">
            <span class="h-2 flex-1 overflow-hidden rounded-full bg-linha"
                  role="progressbar" :aria-valuenow="porcentagem(m)" aria-valuemin="0" aria-valuemax="100"
                  :aria-label="`Progresso em ${m.titulo}`">
              <span class="block h-full rounded-full transition-all"
                    :class="concluido(m) ? 'bg-acerto' : 'bg-caneta'" :style="{ width: `${porcentagem(m)}%` }" />
            </span>
            <span class="shrink-0 text-sm text-tinta-suave">{{ m.n_acertados ?? 0 }}/{{ m.n_exercicios }}</span>
          </span>
          <span v-else class="text-sm text-tinta-suave">Só leitura</span>
        </span>
      </NuxtLink>
    </li>
  </ol>
</template>
