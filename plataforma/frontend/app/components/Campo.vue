<!-- Campo de formulário com rótulo e dica. Use com v-model. -->
<script setup lang="ts">
import { useId } from 'vue'

const modelo = defineModel<string>({ default: '' })
defineProps<{
  rotulo: string
  tipo?: string
  dica?: string
  autocomplete?: string
  obrigatorio?: boolean
}>()
const id = useId()
</script>

<template>
  <div class="flex flex-col gap-1.5">
    <label :for="id" class="text-sm font-medium text-tinta">{{ rotulo }}</label>
    <input
      :id="id"
      v-model="modelo"
      :type="tipo ?? 'text'"
      :autocomplete="autocomplete"
      :required="obrigatorio"
      :aria-describedby="dica ? `${id}-dica` : undefined"
      class="rounded-lg border border-linha bg-white px-3.5 py-2.5 text-tinta placeholder:text-tinta-suave/60 focus:border-caneta"
    >
    <p v-if="dica" :id="`${id}-dica`" class="text-sm text-tinta-suave">{{ dica }}</p>
  </div>
</template>
