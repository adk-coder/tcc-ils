<!-- Professor cria ou edita um exercício de múltipla escolha (2 a 5 alternativas). -->
<script setup lang="ts">
import { useId } from 'vue'
import { letra, type ExercicioProfessor } from '~/utils/tipos'

const props = defineProps<{
  moduloId: number
  ordem: number
  exercicio?: ExercicioProfessor   // presente = editar
}>()
const emit = defineEmits<{ feito: [exercicio: ExercicioProfessor]; cancelar: [] }>()

const MIN = 2
const MAX = 5
const api = useApi()
const grupo = useId()

const enunciado = ref(props.exercicio?.enunciado ?? '')
const alternativas = ref<string[]>(props.exercicio ? [...props.exercicio.alternativas] : ['', '', '', ''])
const correta = ref(props.exercicio?.indice_correta ?? 0)
const explicacao = ref(props.exercicio?.explicacao ?? '')
const pontos = ref(String(props.exercicio?.pontos ?? 10))
const erro = ref('')
const carregando = ref(false)

function adicionar() {
  if (alternativas.value.length < MAX) alternativas.value.push('')
}
function remover(i: number) {
  if (alternativas.value.length <= MIN) return
  alternativas.value.splice(i, 1)
  // mantém a marcação da certa apontando para a mesma alternativa
  if (correta.value === i) correta.value = 0
  else if (correta.value > i) correta.value--
}

async function enviar() {
  erro.value = ''
  if (alternativas.value.some(a => !a.trim())) {
    erro.value = 'Preencha todas as alternativas ou remova as que sobrarem.'
    return
  }
  carregando.value = true
  const corpo = {
    enunciado: enunciado.value.trim(),
    alternativas: alternativas.value.map(a => a.trim()),
    indice_correta: correta.value,
    explicacao: explicacao.value.trim(),
    pontos: Number(pontos.value) || 10,
    ordem: props.ordem,
  }
  try {
    const r = props.exercicio
      ? await api<ExercicioProfessor>(`/exercicios/${props.exercicio.id}`, { method: 'PUT', body: corpo })
      : await api<ExercicioProfessor>(`/modulos/${props.moduloId}/exercicios`, { method: 'POST', body: corpo })
    emit('feito', r)
  } catch (e) {
    erro.value = mensagemDeErro(e)
  } finally {
    carregando.value = false
  }
}
</script>

<template>
  <form class="flex flex-col gap-5" @submit.prevent="enviar">
    <Aviso v-if="erro">{{ erro }}</Aviso>

    <AreaTexto v-model="enunciado" rotulo="Enunciado" :linhas="3" obrigatorio
               dica="Por exemplo: Quanto é 3/4 + 1/2?" />

    <fieldset class="flex flex-col gap-2">
      <legend class="mb-1.5 text-sm font-medium">Alternativas <span class="font-normal text-tinta-suave">— marque a certa</span></legend>
      <div v-for="(_, i) in alternativas" :key="i" class="flex items-center gap-2">
        <label class="flex shrink-0 cursor-pointer items-center gap-2">
          <input v-model="correta" type="radio" :name="grupo" :value="i" class="size-4 accent-acerto">
          <span class="grid size-8 place-items-center rounded-full font-display font-semibold"
                :class="correta === i ? 'bg-acerto text-white' : 'bg-papel text-tinta-suave'">{{ letra(i) }}</span>
          <span class="sr-only">Alternativa {{ letra(i) }} é a certa</span>
        </label>
        <input v-model="alternativas[i]" type="text" :aria-label="`Texto da alternativa ${letra(i)}`"
               class="min-w-0 flex-1 rounded-lg border border-linha bg-white px-3 py-2 focus:border-caneta">
        <button type="button" class="shrink-0 rounded-lg p-2 text-tinta-suave hover:bg-papel hover:text-erro disabled:opacity-30"
                :disabled="alternativas.length <= MIN" :aria-label="`Remover alternativa ${letra(i)}`" @click="remover(i)">
          <Icone nome="lixo" tamanho="p" />
        </button>
      </div>
      <div v-if="alternativas.length < MAX">
        <Botao variante="discreto" pequeno @click="adicionar"><Icone nome="mais" tamanho="p" /> Adicionar alternativa</Botao>
      </div>
    </fieldset>

    <AreaTexto v-model="explicacao" rotulo="Explicação (opcional)" :linhas="3"
               dica="O aluno vê depois de responder. Mostre o caminho da resolução." />

    <div class="max-w-40">
      <Campo v-model="pontos" tipo="number" rotulo="Pontos" dica="De 1 a 100." />
    </div>

    <div class="flex flex-wrap gap-3">
      <Botao tipo="submit" :carregando="carregando">{{ exercicio ? 'Salvar exercício' : 'Adicionar exercício' }}</Botao>
      <Botao variante="discreto" @click="emit('cancelar')">Cancelar</Botao>
    </div>
  </form>
</template>
