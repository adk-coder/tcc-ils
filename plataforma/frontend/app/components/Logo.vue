<!-- Marca do MatIF: o nome com um traço de marca-texto, como num caderno. -->
<script setup lang="ts">
defineProps<{ tamanho?: 'p' | 'g' }>()
</script>

<template>
  <span
    class="font-display font-extrabold tracking-tight text-tinta marca-texto"
    :class="tamanho === 'g' ? 'text-5xl' : 'text-2xl'"
  >MatIF</span>
</template>
