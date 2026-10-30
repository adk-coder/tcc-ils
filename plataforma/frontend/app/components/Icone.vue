<!-- Ícones simples em traço (desenhados como à caneta). -->
<script setup lang="ts">
defineProps<{ nome: 'inicio' | 'salas' | 'conta' | 'sair' }>()
</script>

<template>
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"
       stroke-linejoin="round" class="size-6" aria-hidden="true">
    <template v-if="nome === 'inicio'">
      <path d="M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-4.5v-6h-5v6H5a1 1 0 0 1-1-1z" />
    </template>
    <template v-else-if="nome === 'salas'">
      <rect x="4" y="4" width="7" height="7" rx="1.5" /><rect x="13" y="4" width="7" height="7" rx="1.5" />
      <rect x="4" y="13" width="7" height="7" rx="1.5" /><rect x="13" y="13" width="7" height="7" rx="1.5" />
    </template>
    <template v-else-if="nome === 'conta'">
      <circle cx="12" cy="8.5" r="3.5" /><path d="M5 20c1.2-3.6 4-5.5 7-5.5s5.8 1.9 7 5.5" />
    </template>
    <template v-else>
      <path d="M14 4h4a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-4" /><path d="M10 16l-4-4 4-4" /><path d="M6 12h10" />
    </template>
  </svg>
</template>
