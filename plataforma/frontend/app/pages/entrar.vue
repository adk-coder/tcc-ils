<script setup lang="ts">
definePageMeta({ layout: 'publico' })
useHead({ title: 'Entrar — MatIF' })

const sessao = useSessao()
const email = ref('')
const senha = ref('')
const erro = ref('')
const carregando = ref(false)

async function enviar() {
  erro.value = ''
  carregando.value = true
  try {
    await sessao.entrar(email.value, senha.value)
    await navigateTo('/')
  } catch (e) {
    erro.value = mensagemDeErro(e)
  } finally {
    carregando.value = false
  }
}
</script>

<template>
  <form class="folha flex flex-col gap-5 p-6 sm:p-8" @submit.prevent="enviar">
    <h1 class="text-2xl">Entrar</h1>
    <Aviso v-if="erro">{{ erro }}</Aviso>
    <Campo v-model="email" rotulo="E-mail" tipo="email" autocomplete="email" obrigatorio />
    <Campo v-model="senha" rotulo="Senha" tipo="password" autocomplete="current-password" obrigatorio />
    <Botao tipo="submit" bloco :carregando="carregando">Entrar</Botao>
    <p class="text-center text-sm text-tinta-suave">
      Ainda não tem conta? <NuxtLink to="/cadastro">Criar conta</NuxtLink>
    </p>
  </form>
</template>
