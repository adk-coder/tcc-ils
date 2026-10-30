<!-- Uma sala na lista: folha com o nome; professor vê também código e nº de alunos. -->
<script setup lang="ts">
import type { Sala } from '~/utils/tipos'

defineProps<{ sala: Sala; professor: boolean }>()
</script>

<template>
  <NuxtLink :to="`/salas/${sala.id}`" class="folha block p-5 text-tinta no-underline transition-colors hover:border-caneta">
    <h3 class="text-lg">{{ sala.nome }}</h3>
    <p v-if="professor" class="mt-1 text-sm text-tinta-suave">
      {{ sala.n_alunos }} {{ sala.n_alunos === 1 ? 'aluno' : 'alunos' }} · código
      <span class="font-display font-semibold tracking-wider text-tinta">{{ sala.codigo }}</span>
    </p>
    <p v-else class="mt-1 text-sm text-tinta-suave">Abrir módulos e exercícios</p>
  </NuxtLink>
</template>
