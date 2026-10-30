<!-- Aviso "Novo adesivo!" que aparece no canto quando o aluno ganha uma conquista. -->
<script setup lang="ts">
const { novo } = useConquistas()
let relogio: ReturnType<typeof setTimeout> | undefined

watch(novo, (valor) => {
  clearTimeout(relogio)
  if (valor) relogio = setTimeout(() => (novo.value = null), 6000)
})
onBeforeUnmount(() => clearTimeout(relogio))
</script>

<template>
  <Transition name="troca">
    <div v-if="novo" role="status"
         class="folha pulo fixed bottom-24 right-4 z-20 flex max-w-xs items-center gap-3 p-4 shadow-lg md:bottom-6 md:right-6">
      <Adesivo :adesivo="novo" pequeno />
      <div class="min-w-0">
        <p class="text-sm font-medium text-caneta">Novo adesivo!</p>
        <p class="font-display font-semibold">{{ novo.titulo }}</p>
        <NuxtLink to="/adesivos" class="text-sm" @click="novo = null">Ver meus adesivos</NuxtLink>
      </div>
      <button type="button" class="self-start text-tinta-suave hover:text-tinta" aria-label="Fechar aviso"
              @click="novo = null">×</button>
    </div>
  </Transition>
</template>
