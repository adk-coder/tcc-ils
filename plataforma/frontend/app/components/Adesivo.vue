<!-- Um adesivo de conquista, como uma figurinha colada no caderno:
     ganho  → colorido, com borda branca, sombra e levemente torto;
     falta  → contorno tracejado, apagado, com o progresso (ex.: 3/10). -->
<script setup lang="ts">
import type { Adesivo } from '~/utils/tipos'

const props = withDefaults(defineProps<{ adesivo: Adesivo; indice?: number; pequeno?: boolean }>(),
  { indice: 0, pequeno: false })

// aparência de cada adesivo: cor de fundo + símbolo (ícone ou texto curto)
const VISUAL: Record<string, { fundo: string; icone?: 'certo' | 'refazer' | 'livro' | 'estilo'; texto?: string }> = {
  primeiro_acerto: { fundo: 'bg-acerto text-white', icone: 'certo' },
  na_primeira: { fundo: 'bg-caneta text-white', texto: '1ª' },
  dez_na_conta: { fundo: 'bg-marca text-tinta', texto: '10' },
  nao_desisto: { fundo: 'bg-erro text-white', icone: 'refazer' },
  modulo_fechado: { fundo: 'bg-acerto text-white', icone: 'livro' },
  tres_dias: { fundo: 'bg-marca text-tinta', texto: '3' },
  semana_firme: { fundo: 'bg-caneta text-white', texto: '7' },
  me_conheco: { fundo: 'bg-marca text-tinta', icone: 'estilo' },
}
const visual = computed(() => VISUAL[props.adesivo.id] ?? { fundo: 'bg-caneta text-white', texto: '★' })
const giro = computed(() => [-6, 4, -3, 7, -5, 3, -8, 5][props.indice % 8])
</script>

<template>
  <span
    class="relative grid shrink-0 place-items-center rounded-full font-display font-extrabold"
    :class="[
      pequeno ? 'size-10 text-base' : 'size-20 text-2xl sm:size-24 sm:text-3xl',
      adesivo.ganho
        ? [visual.fundo, 'border-4 border-white shadow-[0_3px_8px_rgba(27,42,65,0.25)]']
        : 'border-2 border-dashed border-linha bg-papel text-tinta-suave/40',
    ]"
    :style="adesivo.ganho ? { transform: `rotate(${giro}deg)` } : undefined"
    aria-hidden="true"
  >
    <Icone v-if="visual.icone" :nome="visual.icone" :tamanho="pequeno ? 'p' : 'g'" />
    <template v-else>{{ visual.texto }}</template>
  </span>
</template>
