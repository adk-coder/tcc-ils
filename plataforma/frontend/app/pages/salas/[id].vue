<!-- Detalhe da sala. Os módulos e o ranking entram na próxima entrega. -->
<script setup lang="ts">
import type { SalaDetalhe } from '~/utils/tipos'

const route = useRoute()
const api = useApi()
const sessao = useSessao()
const id = Number(route.params.id)

const { data: sala, error, refresh } = await useAsyncData(`sala-${id}`, () => api<SalaDetalhe>(`/salas/${id}`))
useHead({ title: () => `${sala.value?.nome ?? 'Sala'} — MatIF` })

const copiado = ref(false)
async function copiarCodigo() {
  if (!sala.value) return
  await navigator.clipboard.writeText(sala.value.codigo)
  copiado.value = true
  setTimeout(() => (copiado.value = false), 2000)
}

const removendo = ref<number | null>(null)
async function removerAluno(alunoId: number) {
  removendo.value = alunoId
  try {
    await api(`/salas/${id}/alunos/${alunoId}`, { method: 'DELETE' })
    await refresh()
  } finally {
    removendo.value = null
  }
}

async function sairDaSala() {
  await api(`/salas/${id}/sair`, { method: 'DELETE' })
  await navigateTo('/salas')
}
</script>

<template>
  <div class="flex flex-col gap-8">
    <NuxtLink to="/salas" class="text-sm">Voltar para salas</NuxtLink>

    <Aviso v-if="error">Sala não encontrada ou você não tem acesso a ela.</Aviso>

    <template v-else-if="sala">
      <header>
        <h1 class="text-3xl">{{ sala.nome }}</h1>
        <p class="mt-1 text-tinta-suave">Professor: {{ sala.professor_nome }}</p>
      </header>

      <!-- professor: código e alunos -->
      <template v-if="sessao.ehProfessor.value">
        <section class="folha flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
          <div>
            <h2 class="text-lg">Código de convite</h2>
            <p class="text-sm text-tinta-suave">Os alunos usam este código para entrar na sala.</p>
          </div>
          <div class="flex items-center gap-3">
            <span class="font-display text-3xl font-extrabold tracking-[0.2em]"><span class="marca-texto">{{ sala.codigo }}</span></span>
            <Botao variante="secundario" @click="copiarCodigo">{{ copiado ? 'Copiado' : 'Copiar' }}</Botao>
          </div>
        </section>

        <section class="flex flex-col gap-3">
          <h2 class="text-xl">Alunos ({{ sala.alunos.length }})</h2>
          <ul v-if="sala.alunos.length" class="folha divide-y divide-linha">
            <li v-for="a in sala.alunos" :key="a.id" class="flex items-center justify-between gap-3 px-5 py-3">
              <span>{{ a.nome }}</span>
              <button type="button" class="text-sm text-erro hover:underline disabled:opacity-60"
                      :disabled="removendo === a.id" @click="removerAluno(a.id)">
                Remover
              </button>
            </li>
          </ul>
          <p v-else class="text-tinta-suave">Nenhum aluno entrou ainda. Passe o código acima para a turma.</p>
        </section>
      </template>

      <!-- aluno -->
      <template v-else>
        <section class="folha p-5 sm:p-6">
          <p>Os módulos de estudo desta sala aparecem aqui em breve.</p>
        </section>
        <div><Botao variante="secundario" @click="sairDaSala">Sair desta sala</Botao></div>
      </template>
    </template>
  </div>
</template>
