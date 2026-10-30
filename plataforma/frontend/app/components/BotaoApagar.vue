<!-- Ação destrutiva em dois cliques (apagar, remover, sair da sala): o 1º pede confirmação, o 2º apaga. Evita apagar sem querer
     sem usar a janela de confirmação do navegador (que é feia e ruim no celular). -->
<script setup lang="ts">
withDefaults(defineProps<{ rotulo?: string; icone?: 'lixo' | 'sair'; carregando?: boolean }>(),
  { rotulo: 'Apagar', icone: 'lixo', carregando: false })
const emit = defineEmits<{ confirmar: [] }>()
const confirmando = ref(false)
let relogio: ReturnType<typeof setTimeout> | undefined

function clicar() {
  if (confirmando.value) {
    clearTimeout(relogio)
    confirmando.value = false
    emit('confirmar')
    return
  }
  confirmando.value = true
  relogio = setTimeout(() => (confirmando.value = false), 4000)   // desiste sozinho
}
onBeforeUnmount(() => clearTimeout(relogio))
</script>

<template>
  <Botao :variante="confirmando ? 'perigo' : 'discreto'" pequeno :carregando="carregando" @click="clicar">
    <Icone :nome="icone" tamanho="p" />
    <span aria-live="polite">{{ confirmando ? 'Clique de novo para confirmar' : rotulo }}</span>
  </Botao>
</template>
