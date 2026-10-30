<!-- Conta: dados do usuário e direitos do titular (LGPD): baixar dados e excluir conta. -->
<script setup lang="ts">
useHead({ title: 'Conta — MatIF' })
const sessao = useSessao()
const api = useApi()
const { $pwa } = useNuxtApp()   // PWA: convite de instalação (só aparece em navegadores que permitem)

const baixando = ref(false)
async function baixarDados() {
  baixando.value = true
  try {
    const dados = await api('/auth/eu/dados')
    const arquivo = new Blob([JSON.stringify(dados, null, 2)], { type: 'application/json' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(arquivo)
    link.download = 'meus-dados-matif.json'
    link.click()
    URL.revokeObjectURL(link.href)
  } finally {
    baixando.value = false
  }
}

const confirmando = ref(false)
const excluindo = ref(false)
async function excluirConta() {
  excluindo.value = true
  try {
    await api('/auth/eu', { method: 'DELETE' })
    await sessao.sair()
  } finally {
    excluindo.value = false
  }
}
</script>

<template>
  <div class="flex flex-col gap-8">
    <h1 class="text-3xl">Conta</h1>

    <section class="folha divide-y divide-linha">
      <div class="px-5 py-4"><p class="text-sm text-tinta-suave">Nome</p><p>{{ sessao.usuario.value?.nome }}</p></div>
      <div class="px-5 py-4"><p class="text-sm text-tinta-suave">E-mail</p><p>{{ sessao.usuario.value?.email }}</p></div>
      <div class="px-5 py-4"><p class="text-sm text-tinta-suave">Perfil</p><p>{{ sessao.ehProfessor.value ? 'Professor' : 'Aluno' }}</p></div>
    </section>

    <section class="flex flex-col gap-3">
      <h2 class="text-xl">Instalar o app</h2>
      <p class="text-tinta-suave">Coloque o MatIF na tela inicial do celular ou do computador e abra como um aplicativo.</p>
      <div v-if="$pwa?.showInstallPrompt"><Botao variante="secundario" @click="$pwa.install()">Instalar o MatIF</Botao></div>
      <p class="text-sm text-tinta-suave">
        No iPhone: toque em <strong>Compartilhar</strong> e depois em <strong>Adicionar à Tela de Início</strong>.
        No Android, se o botão não aparecer, use o menu do navegador → <strong>Instalar app</strong>.
      </p>
    </section>

    <section class="flex flex-col gap-3">
      <h2 class="text-xl">Seus dados</h2>
      <p class="text-tinta-suave">Baixe um arquivo com tudo o que o MatIF guarda sobre você.</p>
      <div><Botao variante="secundario" :carregando="baixando" @click="baixarDados">Baixar meus dados</Botao></div>
    </section>

    <section class="flex flex-col gap-3">
      <h2 class="text-xl">Excluir conta</h2>
      <p class="text-tinta-suave">
        Apaga sua conta e suas respostas. {{ sessao.ehProfessor.value ? 'Suas salas, módulos e exercícios também serão apagados.' : '' }}
        Não dá para desfazer.
      </p>
      <div v-if="!confirmando"><Botao variante="perigo" @click="confirmando = true">Excluir minha conta</Botao></div>
      <div v-else class="folha flex flex-col gap-3 p-5">
        <p class="font-medium">Tem certeza? Esta ação é permanente.</p>
        <div class="flex flex-wrap gap-3">
          <Botao variante="perigo" :carregando="excluindo" @click="excluirConta">Sim, excluir conta</Botao>
          <Botao variante="secundario" @click="confirmando = false">Cancelar</Botao>
        </div>
      </div>
    </section>

    <div class="md:hidden"><Botao variante="secundario" bloco @click="sessao.sair()">Sair</Botao></div>
  </div>
</template>
