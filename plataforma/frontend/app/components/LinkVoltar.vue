<!-- "← Voltar para ..." no topo das páginas internas. -->
<script setup lang="ts">
defineProps<{ para: string }>()
</script>

<template>
  <NuxtLink :to="para" class="inline-flex items-center gap-1.5 self-start text-sm no-underline hover:underline">
    <Icone nome="voltar" tamanho="p" /> <slot />
  </NuxtLink>
</template>
