<!-- Ícones simples em traço (desenhados como à caneta). -->
<script setup lang="ts">
withDefaults(defineProps<{
  nome: 'inicio' | 'salas' | 'conta' | 'sair' | 'voltar' | 'mais' | 'lapis' | 'lixo' | 'certo' | 'trofeu' | 'livro'
  tamanho?: 'p' | 'm'
}>(), { tamanho: 'm' })
</script>

<template>
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"
       stroke-linejoin="round" :class="tamanho === 'p' ? 'size-4' : 'size-6'" aria-hidden="true">
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
    <template v-else-if="nome === 'sair'">
      <path d="M14 4h4a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-4" /><path d="M10 16l-4-4 4-4" /><path d="M6 12h10" />
    </template>
    <template v-else-if="nome === 'voltar'">
      <path d="M19 12H5" /><path d="M11 6l-6 6 6 6" />
    </template>
    <template v-else-if="nome === 'mais'">
      <path d="M12 5v14" /><path d="M5 12h14" />
    </template>
    <template v-else-if="nome === 'lapis'">
      <path d="M4 20l1-4L16 5l3 3L8 19z" /><path d="M14 7l3 3" />
    </template>
    <template v-else-if="nome === 'lixo'">
      <path d="M4 7h16" /><path d="M9 7V4.5h6V7" /><path d="M6 7l1 13h10l1-13" />
    </template>
    <template v-else-if="nome === 'certo'">
      <path d="M4.5 12.5l4.5 4.5L19.5 6.5" />
    </template>
    <template v-else-if="nome === 'trofeu'">
      <path d="M8 4h8v5a4 4 0 0 1-8 0z" /><path d="M8 6H5a3 3 0 0 0 3 4" /><path d="M16 6h3a3 3 0 0 1-3 4" />
      <path d="M12 13v4" /><path d="M8.5 20h7" />
    </template>
    <template v-else>
      <path d="M4 5.5A1.5 1.5 0 0 1 5.5 4H11v16H5.5A1.5 1.5 0 0 1 4 18.5z" />
      <path d="M20 5.5A1.5 1.5 0 0 0 18.5 4H13v16h5.5a1.5 1.5 0 0 0 1.5-1.5z" />
    </template>
  </svg>
</template>
