<!-- Botão padrão. variante: principal (caneta azul), secundario (contorno), perigo. -->
<script setup lang="ts">
withDefaults(defineProps<{
  variante?: 'principal' | 'secundario' | 'perigo'
  tipo?: 'button' | 'submit'
  carregando?: boolean
  bloco?: boolean
}>(), { variante: 'principal', tipo: 'button', carregando: false, bloco: false })
</script>

<template>
  <button
    :type="tipo"
    :disabled="carregando"
    :aria-busy="carregando"
    class="inline-flex items-center justify-center gap-2 rounded-lg px-5 py-3 font-medium transition-colors disabled:opacity-60"
    :class="[
      bloco && 'w-full',
      variante === 'principal' && 'bg-caneta text-white hover:bg-caneta-escura',
      variante === 'secundario' && 'border border-caneta text-caneta bg-white hover:bg-papel',
      variante === 'perigo' && 'bg-erro text-white hover:brightness-95',
    ]"
  >
    <span v-if="carregando" class="size-4 animate-spin rounded-full border-2 border-current border-t-transparent" aria-hidden="true" />
    <slot />
  </button>
</template>
