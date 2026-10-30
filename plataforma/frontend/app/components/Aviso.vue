<!-- Mensagem de erro ou de sucesso, anunciada para leitores de tela. -->
<script setup lang="ts">
defineProps<{ tipo?: 'erro' | 'sucesso' }>()
</script>

<template>
  <p
    role="alert"
    class="rounded-lg border-l-4 px-4 py-3 text-sm"
    :class="tipo === 'sucesso' ? 'border-acerto bg-acerto/10 text-tinta' : 'border-erro bg-erro/10 text-tinta'"
  >
    <slot />
  </p>
</template>
