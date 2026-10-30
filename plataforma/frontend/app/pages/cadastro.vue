<script setup lang="ts">
definePageMeta({ layout: 'publico' })
useHead({ title: 'Criar conta — MatIF' })

const sessao = useSessao()
const dados = reactive({ nome: '', email: '', senha: '', perfil: 'aluno' as 'aluno' | 'professor', aceite_termos: false })
const erro = ref('')
const carregando = ref(false)

async function enviar() {
  erro.value = ''
  if (!dados.aceite_termos) {
    erro.value = mensagemDeErro({ response: true, data: { detail: [{ loc: ['body', 'aceite_termos'] }] } })
    return
  }
  carregando.value = true
  try {
    await sessao.cadastrar({ ...dados })
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
    <h1 class="text-2xl">Criar conta</h1>
    <Aviso v-if="erro">{{ erro }}</Aviso>

    <fieldset class="flex flex-col gap-2">
      <legend class="mb-1.5 text-sm font-medium">Você é</legend>
      <div class="grid grid-cols-2 gap-2">
        <label
          v-for="op in [{ v: 'aluno', t: 'Aluno' }, { v: 'professor', t: 'Professor' }]" :key="op.v"
          class="flex cursor-pointer items-center justify-center rounded-lg border px-3 py-2.5 has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-caneta"
          :class="dados.perfil === op.v ? 'border-caneta bg-caneta/10 font-medium text-caneta' : 'border-linha bg-white'"
        >
          <input v-model="dados.perfil" type="radio" name="perfil" :value="op.v" class="sr-only">
          {{ op.t }}
        </label>
      </div>
    </fieldset>

    <Campo v-model="dados.nome" rotulo="Nome" autocomplete="name" obrigatorio />
    <Campo v-model="dados.email" rotulo="E-mail" tipo="email" autocomplete="email" obrigatorio />
    <Campo v-model="dados.senha" rotulo="Senha" tipo="password" autocomplete="new-password"
           dica="Pelo menos 8 caracteres." obrigatorio />

    <label class="flex items-start gap-3 text-sm">
      <input v-model="dados.aceite_termos" type="checkbox" class="mt-0.5 size-5 accent-caneta">
      <span>
        Li e aceito os termos de uso e a
        <NuxtLink to="/privacidade" target="_blank">política de privacidade</NuxtLink>.
      </span>
    </label>

    <Botao tipo="submit" bloco :carregando="carregando">Criar conta</Botao>
    <p class="text-center text-sm text-tinta-suave">
      Já tem conta? <NuxtLink to="/entrar">Entrar</NuxtLink>
    </p>
  </form>
</template>
