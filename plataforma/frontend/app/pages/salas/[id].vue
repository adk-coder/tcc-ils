<!-- Página da sala: módulos + ranking. O professor vê também o código de convite e os alunos. -->
<script setup lang="ts">
import type { ModuloResumo, SalaDetalhe } from '~/utils/tipos'

const route = useRoute()
const api = useApi()
const sessao = useSessao()
const id = Number(route.params.id)
const professor = sessao.ehProfessor

const { data: sala, error, refresh } = await useAsyncData(`sala-${id}`, () => api<SalaDetalhe>(`/salas/${id}`))
const { data: modulos } = await useAsyncData(`modulos-${id}`,
  () => api<ModuloResumo[]>(`/salas/${id}/modulos`), { default: () => [] })
useHead({ title: () => `${sala.value?.nome ?? 'Sala'} — MatIF` })

// ---- professor: código de convite
const copiado = ref(false)
async function copiarCodigo() {
  if (!sala.value) return
  await navigator.clipboard.writeText(sala.value.codigo)
  copiado.value = true
  setTimeout(() => (copiado.value = false), 2000)
}

// ---- professor: novo módulo (depois de criar, já abre o módulo para pôr exercícios)
const criandoModulo = ref(false)
function moduloCriado(m: ModuloResumo) {
  criandoModulo.value = false
  return navigateTo(`/modulos/${m.id}`)
}

// ---- professor: remover aluno
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

// ---- aluno: sair da sala
async function sairDaSala() {
  await api(`/salas/${id}/sair`, { method: 'DELETE' })
  await navigateTo('/salas')
}
</script>

<template>
  <div class="flex flex-col gap-8">
    <LinkVoltar para="/salas">Voltar para salas</LinkVoltar>

    <Aviso v-if="error">Sala não encontrada ou você não tem acesso a ela.</Aviso>

    <template v-else-if="sala">
      <header>
        <h1 class="text-3xl md:text-4xl">{{ sala.nome }}</h1>
        <p class="mt-1 text-tinta-suave">Professor: {{ sala.professor_nome }}</p>
      </header>

      <!-- professor: código de convite -->
      <section v-if="professor" class="folha flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
        <div>
          <h2 class="text-lg">Código de convite</h2>
          <p class="text-sm text-tinta-suave">Os alunos usam este código para entrar na sala.</p>
        </div>
        <div class="flex items-center gap-3">
          <span class="font-display text-3xl font-extrabold tracking-[0.2em]"><span class="marca-texto">{{ sala.codigo }}</span></span>
          <Botao variante="secundario" @click="copiarCodigo">{{ copiado ? 'Copiado' : 'Copiar' }}</Botao>
        </div>
      </section>

      <!-- módulos + ranking (lado a lado em telas grandes) -->
      <div class="grid gap-8 lg:grid-cols-[minmax(0,1fr)_16rem] lg:items-start">
        <section class="flex flex-col gap-4" aria-labelledby="titulo-modulos">
          <div class="flex items-center justify-between gap-3">
            <h2 id="titulo-modulos" class="text-xl">Módulos</h2>
            <Botao v-if="professor && !criandoModulo" variante="secundario" pequeno @click="criandoModulo = true">
              <Icone nome="mais" tamanho="p" /> Novo módulo
            </Botao>
          </div>

          <div v-if="criandoModulo" class="folha p-5 sm:p-6">
            <h3 class="mb-4 text-lg">Novo módulo</h3>
            <FormModulo :sala-id="id" :ordem="modulos.length + 1" @feito="moduloCriado" @cancelar="criandoModulo = false" />
          </div>

          <ListaModulos v-if="modulos.length" :modulos="modulos" :professor="professor" />
          <p v-else-if="!criandoModulo" class="folha p-5 text-tinta-suave sm:p-6">
            {{ professor
              ? 'Nenhum módulo ainda. Crie o primeiro: um texto curto de estudo e alguns exercícios.'
              : 'O professor ainda não publicou módulos nesta sala. Volte daqui a pouco!' }}
          </p>
        </section>

        <aside class="lg:sticky lg:top-6">
          <Ranking :sala-id="id" />
        </aside>
      </div>

      <!-- professor: alunos -->
      <section v-if="professor" class="flex flex-col gap-3">
        <h2 class="text-xl">Alunos ({{ sala.alunos.length }})</h2>
        <ul v-if="sala.alunos.length" class="folha divide-y divide-linha">
          <li v-for="a in sala.alunos" :key="a.id" class="flex items-center justify-between gap-3 px-5 py-2.5">
            <span>{{ a.nome }}</span>
            <BotaoApagar rotulo="Remover" :carregando="removendo === a.id" @confirmar="removerAluno(a.id)" />
          </li>
        </ul>
        <p v-else class="text-tinta-suave">Nenhum aluno entrou ainda. Passe o código acima para a turma.</p>
      </section>

      <!-- aluno: sair -->
      <div v-else class="border-t border-linha pt-4">
        <BotaoApagar rotulo="Sair desta sala" icone="sair" @confirmar="sairDaSala" />
      </div>
    </template>
  </div>
</template>
