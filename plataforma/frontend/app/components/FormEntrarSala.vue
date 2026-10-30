<!-- Aluno entra numa sala com o código passado pelo professor. -->
<script setup lang="ts">
import type { Sala } from '~/utils/tipos'

const emit = defineEmits<{ feito: [sala: Sala] }>()
const api = useApi()
const codigo = ref('')
const erro = ref('')
const carregando = ref(false)

async function enviar() {
  erro.value = ''
  carregando.value = true
  try {
    const sala = await api<Sala>('/salas/entrar', { method: 'POST', body: { codigo: codigo.value.trim() } })
    codigo.value = ''
    emit('feito', sala)
  } catch (e) {
    erro.value = mensagemDeErro(e)
  } finally {
    carregando.value = false
  }
}
</script>

<template>
  <form class="flex flex-col gap-3" @submit.prevent="enviar">
    <Aviso v-if="erro">{{ erro }}</Aviso>
    <div class="flex flex-col gap-3 sm:flex-row sm:items-end">
      <div class="flex-1">
        <Campo v-model="codigo" rotulo="Código da sala" dica="Peça ao seu professor. São 6 letras e números." obrigatorio />
      </div>
      <Botao tipo="submit" :carregando="carregando" class="sm:mb-7">Entrar na sala</Botao>
    </div>
  </form>
</template>
