<!-- Professor cria uma sala; a API gera o código de convite. -->
<script setup lang="ts">
import type { Sala } from '~/utils/tipos'

const emit = defineEmits<{ feito: [sala: Sala] }>()
const api = useApi()
const nome = ref('')
const erro = ref('')
const carregando = ref(false)

async function enviar() {
  erro.value = ''
  carregando.value = true
  try {
    const sala = await api<Sala>('/salas', { method: 'POST', body: { nome: nome.value.trim() } })
    nome.value = ''
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
        <Campo v-model="nome" rotulo="Nome da sala" dica="Por exemplo: Partiu IF 2026 — turma da manhã" obrigatorio />
      </div>
      <Botao tipo="submit" :carregando="carregando" class="sm:mb-7">Criar sala</Botao>
    </div>
  </form>
</template>
