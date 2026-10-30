<!-- Botão padrão. variante: principal (caneta azul), secundario (contorno), perigo, discreto (só texto). -->
<script setup lang="ts">
withDefaults(defineProps<{
  variante?: 'principal' | 'secundario' | 'perigo' | 'discreto'
  tipo?: 'button' | 'submit'
  carregando?: boolean
  desabilitado?: boolean
  bloco?: boolean
  pequeno?: boolean
}>(), { variante: 'principal', tipo: 'button', carregando: false, desabilitado: false, bloco: false, pequeno: false })
</script>

<template>
  <button
    :type="tipo"
    :disabled="carregando || desabilitado"
    :aria-busy="carregando"
    class="inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50"
    :class="[
      bloco && 'w-full',
      pequeno ? 'px-3 py-1.5 text-sm' : 'px-5 py-3',
      variante === 'principal' && 'bg-caneta text-white hover:bg-caneta-escura',
      variante === 'secundario' && 'border border-caneta bg-white text-caneta hover:bg-papel',
      variante === 'perigo' && 'bg-erro text-white hover:brightness-95',
      variante === 'discreto' && 'text-tinta-suave hover:bg-papel hover:text-tinta',
    ]"
  >
    <span v-if="carregando" class="size-4 animate-spin rounded-full border-2 border-current border-t-transparent" aria-hidden="true" />
    <slot />
  </button>
</template>
