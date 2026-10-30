<!-- Campo de texto com várias linhas (enunciados, explicações, texto do módulo). Use com v-model. -->
<script setup lang="ts">
import { useId } from 'vue'

const modelo = defineModel<string>({ default: '' })
withDefaults(defineProps<{
  rotulo: string
  dica?: string
  linhas?: number
  obrigatorio?: boolean
}>(), { linhas: 4 })
const id = useId()
</script>

<template>
  <div class="flex flex-col gap-1.5">
    <label :for="id" class="text-sm font-medium text-tinta">{{ rotulo }}</label>
    <textarea
      :id="id"
      v-model="modelo"
      :rows="linhas"
      :required="obrigatorio"
      :aria-describedby="dica ? `${id}-dica` : undefined"
      class="resize-y rounded-lg border border-linha bg-white px-3.5 py-2.5 text-tinta focus:border-caneta"
    />
    <p v-if="dica" :id="`${id}-dica`" class="text-sm text-tinta-suave">{{ dica }}</p>
  </div>
</template>
