<!-- Uma pergunta do questionário de estilos: enunciado + alternativas (a) e (b).
     Ao tocar numa alternativa, o círculo de caneta se desenha e a resposta é enviada.
     Não há "certo" nem "errado", então não há botão de confirmar. -->
<script setup lang="ts">
import type { PerguntaEstilo } from '~/utils/tipos'

const props = defineProps<{ pergunta: PerguntaEstilo; enviando: boolean }>()
const emit = defineEmits<{ escolher: [resposta: 'a' | 'b'] }>()

const escolhida = ref<'a' | 'b' | null>(null)
const opcoes = computed(() => [
  { resposta: 'a' as const, letra: 'A', texto: props.pergunta.alternativa_a },
  { resposta: 'b' as const, letra: 'B', texto: props.pergunta.alternativa_b },
])

function escolher(r: 'a' | 'b') {
  if (escolhida.value || props.enviando) return
  escolhida.value = r
  setTimeout(() => emit('escolher', r), 320)   // tempo de o círculo terminar de se desenhar
}
</script>

<template>
  <section class="folha p-6 sm:p-8" aria-live="polite">
    <p class="text-sm text-tinta-suave">Pergunta {{ pergunta.numero }}</p>
    <h2 class="mt-2 font-sans text-xl font-medium leading-snug sm:text-2xl">{{ pergunta.enunciado }}</h2>

    <div class="mt-6 flex flex-col gap-3" role="group" aria-label="Escolha uma alternativa">
      <button
        v-for="op in opcoes" :key="op.resposta" type="button"
        :disabled="!!escolhida || enviando" :aria-pressed="escolhida === op.resposta"
        class="flex items-center gap-4 rounded-lg border px-4 py-3.5 text-left transition-colors"
        :class="escolhida === op.resposta
          ? 'border-caneta bg-caneta/5'
          : 'border-linha bg-white hover:border-caneta/50 disabled:opacity-50'"
        @click="escolher(op.resposta)"
      >
        <span class="relative grid size-9 shrink-0 place-items-center font-display text-lg font-semibold">
          {{ op.letra }}
          <CirculoCaneta v-if="escolhida === op.resposta" class="text-caneta" />
        </span>
        <span>{{ op.texto }}</span>
      </button>
    </div>
  </section>
</template>
