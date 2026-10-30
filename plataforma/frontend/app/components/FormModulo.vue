<!-- Professor cria ou edita um módulo (título + texto de estudo). -->
<script setup lang="ts">
import type { ModuloResumo } from '~/utils/tipos'

const props = defineProps<{
  salaId: number
  ordem: number
  modulo?: { id: number; titulo: string; conteudo: string; ordem: number }   // presente = editar
}>()
const emit = defineEmits<{ feito: [modulo: ModuloResumo]; cancelar: [] }>()

const api = useApi()
const titulo = ref(props.modulo?.titulo ?? '')
const conteudo = ref(props.modulo?.conteudo ?? '')
const erro = ref('')
const carregando = ref(false)

async function enviar() {
  erro.value = ''
  carregando.value = true
  const corpo = { titulo: titulo.value.trim(), conteudo: conteudo.value, ordem: props.modulo?.ordem ?? props.ordem }
  try {
    const r = props.modulo
      ? await api<ModuloResumo>(`/modulos/${props.modulo.id}`, { method: 'PUT', body: corpo })
      : await api<ModuloResumo>(`/salas/${props.salaId}/modulos`, { method: 'POST', body: corpo })
    emit('feito', r)
  } catch (e) {
    erro.value = mensagemDeErro(e)
  } finally {
    carregando.value = false
  }
}
</script>

<template>
  <form class="flex flex-col gap-4" @submit.prevent="enviar">
    <Aviso v-if="erro">{{ erro }}</Aviso>
    <Campo v-model="titulo" rotulo="Título do módulo" dica="Por exemplo: Frações — somar e subtrair" obrigatorio />
    <AreaTexto v-model="conteudo" rotulo="Texto de estudo" :linhas="8"
               dica="Explique o conteúdo antes dos exercícios. Pule uma linha para começar outro parágrafo." />
    <div class="flex flex-wrap gap-3">
      <Botao tipo="submit" :carregando="carregando">{{ modulo ? 'Salvar módulo' : 'Criar módulo' }}</Botao>
      <Botao variante="discreto" @click="emit('cancelar')">Cancelar</Botao>
    </div>
  </form>
</template>
