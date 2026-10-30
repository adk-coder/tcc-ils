<!-- "Meu estilo": questionário adaptativo de estilos de aprendizagem (só alunos).
     Quem escolhe cada pergunta e decide quando parar é o backend (app/ils/motor.py,
     o TAC exportado da parte de IA do TCC). Esta página só mostra e envia as respostas. -->
<script setup lang="ts">
import type { EstadoEstilo } from '~/utils/tipos'
import { DIMENSOES } from '~/utils/estilos'

useHead({ title: 'Meu estilo — MatIF' })
const sessao = useSessao()
const api = useApi()
if (sessao.ehProfessor.value) await navigateTo('/')

const { data: estado, error, refresh } = await useAsyncData('estilo', () => api<EstadoEstilo>('/eu/estilo'))
const indisponivel = computed(() => error.value?.statusCode === 503)

const enviando = ref(false)
const erro = ref('')
const confirmarRefazer = ref(false)
const tentativa = ref(0)          // muda a chave do cartão para destravar depois de um erro

async function iniciar() {
  enviando.value = true
  erro.value = ''
  try {
    estado.value = await api<EstadoEstilo>('/eu/estilo/iniciar', { method: 'POST' })
    confirmarRefazer.value = false
    clearNuxtData('inicio-estilo')
  } catch (e) {
    erro.value = mensagemDeErro(e)
  } finally {
    enviando.value = false
  }
}

async function responder(resposta: 'a' | 'b') {
  const pergunta = estado.value?.pergunta
  if (!pergunta) return
  enviando.value = true
  erro.value = ''
  try {
    estado.value = await api<EstadoEstilo>('/eu/estilo/responder', {
      method: 'POST', body: { item: pergunta.item, resposta },
    })
    if (estado.value.status === 'concluido') {
      clearNuxtData('inicio-estilo')
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  } catch (e) {
    erro.value = mensagemDeErro(e)
    tentativa.value++
    await refresh()        // ex.: resposta duplicada (409) → volta para a pergunta atual
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <div class="flex flex-col gap-8">
    <header>
      <h1 class="text-3xl md:text-4xl">Meu estilo de aprendizagem</h1>
      <p class="mt-1 text-tinta-suave">Descubra como você prefere aprender e receba dicas de estudo.</p>
    </header>

    <Aviso v-if="estado?.textos_provisorios">
      Modo de desenvolvimento: as perguntas ainda são textos provisórios (preencha
      <code>plataforma/backend/app/ils/itens.json</code> com a versão oficial do questionário).
    </Aviso>
    <Aviso v-if="indisponivel">O questionário ainda não está disponível. Tente de novo mais tarde.</Aviso>
    <Aviso v-else-if="error">Não foi possível carregar o questionário. Confira se a API está rodando.</Aviso>
    <Aviso v-if="erro">{{ erro }}</Aviso>

    <template v-if="estado && !error">
      <!-- 1. apresentação -->
      <section v-if="estado.status === 'nao_iniciado'" class="folha flex flex-col gap-4 p-6 sm:p-8">
        <h2 class="text-2xl">Como você aprende melhor?</h2>
        <p>
          Este questionário mostra suas preferências em quatro aspectos do jeito de aprender. Não existe resposta
          certa nem errada: escolha a opção que mais combina com você, mesmo que as duas pareçam um pouco verdadeiras.
        </p>
        <ul class="flex flex-wrap gap-2" aria-label="Os quatro aspectos">
          <li v-for="(dim, chave) in DIMENSOES" :key="chave"
              class="rounded-full bg-caneta/10 px-3 py-1 text-sm text-caneta">{{ dim.pergunta }}</li>
        </ul>
        <p class="text-tinta-suave">
          O questionário original tem 44 perguntas. Aqui, uma inteligência artificial escolhe as perguntas mais úteis
          para você e para assim que tem segurança do resultado. Por isso, geralmente são bem menos.
        </p>
        <div><Botao :carregando="enviando" @click="iniciar">Começar</Botao></div>
      </section>

      <!-- 2. perguntas -->
      <template v-else-if="estado.status === 'em_andamento' && estado.pergunta">
        <div class="flex flex-wrap items-center gap-3">
          <div class="flex gap-1.5" role="progressbar" :aria-valuenow="estado.partes_concluidas"
               aria-valuemin="0" aria-valuemax="4" aria-label="Partes concluídas">
            <span v-for="i in 4" :key="i" class="h-2 w-10 rounded-full transition-colors duration-500"
                  :class="i <= estado.partes_concluidas ? 'bg-caneta' : 'bg-linha'" />
          </div>
          <span class="text-sm text-tinta-suave">{{ estado.partes_concluidas }} de 4 partes concluídas</span>
        </div>

        <Transition name="troca" mode="out-in">
          <CartaoPerguntaEstilo :key="`${estado.pergunta.item}-${tentativa}`" :pergunta="estado.pergunta" :enviando="enviando"
                                @escolher="responder" />
        </Transition>
        <p class="text-sm text-tinta-suave">Pode parar quando quiser: suas respostas ficam salvas e você continua depois.</p>
      </template>

      <!-- 3. resultado -->
      <template v-else-if="estado.status === 'concluido' && estado.resultado">
        <p class="text-lg">
          Pronto! Você respondeu <strong class="font-display"><span class="marca-texto">{{ estado.respondidas }} perguntas</span></strong>
          em vez de 44.
        </p>
        <ResultadoEstilo :resultado="estado.resultado" />
        <p class="folha p-5 text-sm text-tinta-suave">
          Lembre: isto mostra <strong class="text-tinta">preferências</strong>, não limites. Todo mundo usa os dois lados
          de cada par, e treinar o lado de que você gosta menos também ajuda a aprender.
        </p>
        <div class="flex flex-wrap items-center gap-3 border-t border-linha pt-4">
          <Botao v-if="!confirmarRefazer" variante="discreto" pequeno @click="confirmarRefazer = true">Refazer o questionário</Botao>
          <template v-else>
            <span class="text-sm">O resultado atual será apagado. Refazer?</span>
            <Botao pequeno :carregando="enviando" @click="iniciar">Sim, refazer</Botao>
            <Botao variante="discreto" pequeno @click="confirmarRefazer = false">Cancelar</Botao>
          </template>
        </div>
      </template>
    </template>
  </div>
</template>
