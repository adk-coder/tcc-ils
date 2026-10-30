<!-- Página do módulo: texto de estudo + exercícios.
     Aluno: lê e responde (com correção na hora). Professor: edita o texto e monta os exercícios. -->
<script setup lang="ts">
import type { ExercicioAluno, ExercicioProfessor, ModuloDetalhe, RespostaSaida } from '~/utils/tipos'

const route = useRoute()
const api = useApi()
const sessao = useSessao()
const id = Number(route.params.id)
const professor = sessao.ehProfessor

const { data: modulo, error, refresh } = await useAsyncData(`modulo-${id}`, () => api<ModuloDetalhe>(`/modulos/${id}`))
useHead({ title: () => `${modulo.value?.titulo ?? 'Módulo'} — MatIF` })

// a API manda formatos diferentes para aluno e professor (ver esquemas.py)
const exerciciosAluno = computed(() => (modulo.value?.exercicios ?? []) as ExercicioAluno[])
const exerciciosProfessor = computed(() => (modulo.value?.exercicios ?? []) as ExercicioProfessor[])
const total = computed(() => modulo.value?.exercicios.length ?? 0)
const acertados = computed(() => exerciciosAluno.value.filter(e => e.ja_acertou).length)
const concluido = computed(() => !professor.value && total.value > 0 && acertados.value === total.value)

// texto de estudo: uma linha em branco separa parágrafos
const paragrafos = computed(() =>
  (modulo.value?.conteudo ?? '').split(/\n\s*\n/).map(p => p.trim()).filter(Boolean))

// aluno respondeu: atualiza a barra de progresso sem recarregar a página e descarta
// os dados guardados que ficaram velhos (progresso na sala, ranking e pontos do início),
// para que sejam buscados de novo na API quando o aluno voltar para essas telas
function registrar(exercicio: ExercicioAluno, r: RespostaSaida) {
  exercicio.ja_respondeu = true
  if (r.correta) exercicio.ja_acertou = true
  clearNuxtData(chave => chave.startsWith('modulos-') || chave.startsWith('ranking-') || chave === 'inicio-progresso')
}

// ---- professor
const editando = ref(false)
const novoExercicio = ref(false)
const apagando = ref(false)
const erro = ref('')
const proximaOrdem = computed(() => Math.max(0, ...exerciciosProfessor.value.map(e => e.ordem)) + 1)

async function apagarModulo() {
  if (!modulo.value) return
  apagando.value = true
  erro.value = ''
  try {
    const sala = modulo.value.sala_id
    await api(`/modulos/${id}`, { method: 'DELETE' })
    await navigateTo(`/salas/${sala}`)
  } catch (e) {
    erro.value = mensagemDeErro(e)
  } finally {
    apagando.value = false
  }
}
</script>

<template>
  <div class="flex flex-col gap-8">
    <LinkVoltar :para="modulo ? `/salas/${modulo.sala_id}` : '/salas'">Voltar para a sala</LinkVoltar>

    <Aviso v-if="error">Módulo não encontrado ou você não tem acesso a ele.</Aviso>

    <template v-else-if="modulo">
      <!-- professor editando título/texto -->
      <section v-if="editando" class="folha p-5 sm:p-6">
        <h1 class="mb-4 text-2xl">Editar módulo</h1>
        <FormModulo :sala-id="modulo.sala_id" :ordem="modulo.ordem" :modulo="modulo"
                    @feito="editando = false; refresh()" @cancelar="editando = false" />
      </section>

      <template v-else>
        <header class="flex flex-col gap-3">
          <h1 class="text-3xl md:text-4xl">{{ modulo.titulo }}</h1>

          <!-- aluno: progresso no módulo -->
          <div v-if="!professor && total" class="flex max-w-sm items-center gap-3">
            <span class="h-2.5 flex-1 overflow-hidden rounded-full bg-linha" role="progressbar"
                  :aria-valuenow="acertados" aria-valuemin="0" :aria-valuemax="total" aria-label="Exercícios certos">
              <span class="block h-full rounded-full transition-all duration-500"
                    :class="concluido ? 'bg-acerto' : 'bg-caneta'" :style="{ width: `${100 * acertados / total}%` }" />
            </span>
            <span class="shrink-0 text-sm text-tinta-suave">{{ acertados }} de {{ total }} certos</span>
          </div>

          <!-- professor: ações do módulo -->
          <div v-if="professor" class="flex flex-wrap gap-1">
            <Botao variante="discreto" pequeno @click="editando = true"><Icone nome="lapis" tamanho="p" /> Editar módulo</Botao>
            <BotaoApagar rotulo="Apagar módulo" :carregando="apagando" @confirmar="apagarModulo" />
          </div>
          <Aviso v-if="erro">{{ erro }}</Aviso>
        </header>

        <section v-if="paragrafos.length" class="folha-caderno" aria-labelledby="titulo-estudo">
          <h2 id="titulo-estudo" class="mb-3 flex items-center gap-2 text-lg">
            <Icone nome="livro" class="text-caneta" /> Para estudar
          </h2>
          <div class="flex max-w-prose flex-col gap-3 leading-relaxed">
            <p v-for="(p, i) in paragrafos" :key="i" class="whitespace-pre-line">{{ p }}</p>
          </div>
        </section>
        <p v-else-if="professor" class="folha p-5 text-tinta-suave sm:p-6">
          Este módulo ainda não tem texto de estudo. Use "Editar módulo" para escrever.
        </p>
      </template>

      <!-- exercícios -->
      <section class="flex flex-col gap-4" aria-labelledby="titulo-exercicios">
        <h2 id="titulo-exercicios" class="text-xl">Exercícios</h2>

        <template v-if="professor">
          <ExercicioGabarito v-for="(e, i) in exerciciosProfessor" :key="e.id" :exercicio="e" :numero="i + 1"
                             @mudou="refresh()" />
          <p v-if="!total && !novoExercicio" class="text-tinta-suave">Nenhum exercício ainda.</p>
          <div v-if="novoExercicio" class="folha p-5 sm:p-6">
            <h3 class="mb-4 text-lg">Novo exercício</h3>
            <FormExercicio :modulo-id="modulo.id" :ordem="proximaOrdem"
                           @feito="novoExercicio = false; refresh()" @cancelar="novoExercicio = false" />
          </div>
          <div v-else>
            <Botao @click="novoExercicio = true"><Icone nome="mais" tamanho="p" /> Novo exercício</Botao>
          </div>
        </template>

        <template v-else>
          <ExercicioResponder v-for="(e, i) in exerciciosAluno" :key="e.id" :exercicio="e" :numero="i + 1"
                              @respondido="(r) => registrar(e, r)" />
          <p v-if="!total" class="folha p-5 text-tinta-suave sm:p-6">Este módulo não tem exercícios, é só leitura.</p>

          <div v-if="concluido" class="folha flex flex-col items-center gap-2 p-6 text-center" aria-live="polite">
            <p class="font-display text-2xl font-extrabold"><span class="marca-texto">Módulo concluído!</span></p>
            <p class="text-tinta-suave">Você acertou todos os exercícios deste módulo.</p>
            <NuxtLink :to="`/salas/${modulo.sala_id}`" class="mt-2 font-medium">Escolher o próximo módulo</NuxtLink>
          </div>
        </template>
      </section>
    </template>
  </div>
</template>
