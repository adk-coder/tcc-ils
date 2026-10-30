<!-- Exercício na visão do ALUNO.
     1. escolhe a alternativa → um círculo "à caneta" se desenha em volta da letra;
     2. clica em Responder → a API corrige;
     3. a certa ganha marca-texto; se errou, a escolhida fica riscada em vermelho;
     4. aparecem os pontos (só na 1ª tentativa certa, regra do backend) e a explicação. -->
<script setup lang="ts">
import { useId } from 'vue'
import { letra, type ExercicioAluno, type RespostaSaida } from '~/utils/tipos'

const props = defineProps<{ exercicio: ExercicioAluno; numero: number }>()
const emit = defineEmits<{ respondido: [resposta: RespostaSaida] }>()

const api = useApi()
const nomeGrupo = useId()
const escolhida = ref<number | null>(null)
const resultado = ref<RespostaSaida | null>(null)
const enviando = ref(false)
const erro = ref('')

async function responder() {
  if (escolhida.value === null) return
  erro.value = ''
  enviando.value = true
  try {
    resultado.value = await api<RespostaSaida>(`/exercicios/${props.exercicio.id}/responder`, {
      method: 'POST', body: { alternativa: escolhida.value },
    })
    emit('respondido', resultado.value)
  } catch (e) {
    erro.value = mensagemDeErro(e)
  } finally {
    enviando.value = false
  }
}

function refazer() {
  resultado.value = null
  escolhida.value = null
}

// aparência de cada alternativa, antes e depois da correção
function classeCaixa(i: number) {
  const r = resultado.value
  if (!r) {
    return escolhida.value === i
      ? 'border-caneta bg-caneta/5'
      : 'border-linha bg-white hover:border-caneta/50 cursor-pointer'
  }
  if (i === r.indice_correta) return 'border-acerto bg-acerto/5'
  if (i === escolhida.value) return 'border-erro bg-erro/5'
  return 'border-linha bg-white opacity-60'
}
function classeTexto(i: number) {
  const r = resultado.value
  if (r && i === r.indice_correta) return 'marca-texto font-medium'
  if (r && i === escolhida.value) return 'line-through decoration-erro decoration-2'
  return ''
}
const corDaCaneta = computed(() => {
  const r = resultado.value
  if (!r) return 'text-caneta'
  return r.correta ? 'text-acerto' : 'text-erro'
})
</script>

<template>
  <article class="folha p-5 sm:p-6" :aria-labelledby="`${nomeGrupo}-titulo`">
    <header class="mb-3 flex flex-wrap items-center justify-between gap-2">
      <h3 :id="`${nomeGrupo}-titulo`" class="text-base text-tinta-suave">Exercício {{ numero }}</h3>
      <span v-if="exercicio.ja_acertou && !resultado"
            class="inline-flex items-center gap-1 rounded-full bg-acerto/10 px-2.5 py-0.5 text-sm font-medium text-acerto">
        <Icone nome="certo" tamanho="p" /> Você já acertou
      </span>
      <span v-else-if="!exercicio.ja_respondeu && !resultado" class="text-sm text-tinta-suave">
        vale <strong class="font-display text-tinta">{{ exercicio.pontos }}</strong> pontos
      </span>
    </header>

    <p class="mb-5 whitespace-pre-line text-lg">{{ exercicio.enunciado }}</p>

    <fieldset :disabled="!!resultado || enviando">
      <legend class="sr-only">Alternativas do exercício {{ numero }}</legend>
      <div class="flex flex-col gap-2.5">
        <label v-for="(alt, i) in exercicio.alternativas" :key="i"
               class="flex items-center gap-3 rounded-lg border px-3 py-2.5 transition-colors has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-caneta"
               :class="classeCaixa(i)">
          <input v-model="escolhida" type="radio" class="sr-only" :name="nomeGrupo" :value="i">
          <!-- letra + círculo de caneta -->
          <span class="relative grid size-9 shrink-0 place-items-center font-display text-lg font-semibold">
            {{ letra(i) }}
            <svg v-if="escolhida === i" viewBox="0 0 48 48" fill="none" aria-hidden="true"
                 class="pointer-events-none absolute left-1/2 top-1/2 size-12 -translate-x-1/2 -translate-y-1/2"
                 :class="corDaCaneta">
              <path class="traco-caneta" pathLength="1" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"
                    d="M31 7.5C18 3.5 6 12 6.5 25c.5 12.5 13.5 19.5 26 15C43.5 36 45 19.5 36.5 11.5 32 7.5 25 6 19 8.5" />
            </svg>
          </span>
          <!-- span interno: o marca-texto cobre só o texto, não a linha inteira -->
          <span class="flex-1"><span :class="classeTexto(i)">{{ alt }}</span></span>
          <Icone v-if="resultado && i === resultado.indice_correta" nome="certo" class="shrink-0 text-acerto" />
        </label>
      </div>
    </fieldset>

    <Aviso v-if="erro" class="mt-4">{{ erro }}</Aviso>

    <!-- antes de responder -->
    <div v-if="!resultado" class="mt-5">
      <Botao :desabilitado="escolhida === null" :carregando="enviando" @click="responder">Responder</Botao>
    </div>

    <!-- depois de responder -->
    <div v-else class="mt-5 flex flex-col gap-4" aria-live="polite">
      <p class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <strong class="font-display text-xl" :class="resultado.correta ? 'text-acerto' : 'text-erro'">
          {{ resultado.correta ? 'Isso aí!' : 'Não foi dessa vez.' }}
        </strong>
        <span v-if="resultado.pontos_ganhos > 0" class="pulo font-display text-xl font-extrabold">
          <span class="marca-texto">+{{ resultado.pontos_ganhos }} pontos</span>
        </span>
        <span v-else-if="resultado.correta" class="text-sm text-tinta-suave">Refazer não vale pontos, mas vale treino.</span>
        <span v-else class="text-sm text-tinta-suave">A resposta certa está marcada.</span>
      </p>

      <div v-if="resultado.explicacao" class="rounded-lg border-l-4 border-caneta bg-caneta/5 px-4 py-3">
        <p class="mb-1 text-sm font-medium text-caneta">Explicação</p>
        <p class="whitespace-pre-line">{{ resultado.explicacao }}</p>
      </div>

      <div><Botao variante="secundario" pequeno @click="refazer">Refazer</Botao></div>
    </div>
  </article>
</template>
