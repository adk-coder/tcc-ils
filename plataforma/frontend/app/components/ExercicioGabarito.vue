<!-- Exercício na visão do PROFESSOR: mostra o gabarito e permite editar ou apagar. -->
<script setup lang="ts">
import { letra, type ExercicioProfessor } from '~/utils/tipos'

const props = defineProps<{ exercicio: ExercicioProfessor; numero: number }>()
const emit = defineEmits<{ mudou: [] }>()

const api = useApi()
const editando = ref(false)
const apagando = ref(false)
const erro = ref('')

async function apagar() {
  apagando.value = true
  erro.value = ''
  try {
    await api(`/exercicios/${props.exercicio.id}`, { method: 'DELETE' })
    emit('mudou')
  } catch (e) {
    erro.value = mensagemDeErro(e)
  } finally {
    apagando.value = false
  }
}
</script>

<template>
  <article class="folha p-5 sm:p-6">
    <template v-if="editando">
      <h3 class="mb-4 text-lg">Editar exercício {{ numero }}</h3>
      <FormExercicio :modulo-id="exercicio.modulo_id" :ordem="exercicio.ordem" :exercicio="exercicio"
                     @feito="editando = false; emit('mudou')" @cancelar="editando = false" />
    </template>

    <template v-else>
      <header class="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h3 class="text-base text-tinta-suave">Exercício {{ numero }} · {{ exercicio.pontos }} pontos</h3>
        <div class="flex gap-1">
          <Botao variante="discreto" pequeno @click="editando = true"><Icone nome="lapis" tamanho="p" /> Editar</Botao>
          <BotaoApagar :carregando="apagando" @confirmar="apagar" />
        </div>
      </header>
      <Aviso v-if="erro" class="mb-3">{{ erro }}</Aviso>

      <p class="mb-4 whitespace-pre-line text-lg">{{ exercicio.enunciado }}</p>
      <ul class="flex flex-col gap-1.5">
        <li v-for="(alt, i) in exercicio.alternativas" :key="i" class="flex items-center gap-3">
          <span class="grid size-7 shrink-0 place-items-center rounded-full font-display text-sm font-semibold"
                :class="i === exercicio.indice_correta ? 'bg-acerto text-white' : 'bg-papel text-tinta-suave'">
            {{ letra(i) }}
          </span>
          <span :class="i === exercicio.indice_correta && 'marca-texto font-medium'">{{ alt }}</span>
          <span v-if="i === exercicio.indice_correta" class="sr-only">(resposta certa)</span>
        </li>
      </ul>
      <p v-if="exercicio.explicacao" class="mt-4 whitespace-pre-line border-l-4 border-linha pl-3 text-sm text-tinta-suave">
        {{ exercicio.explicacao }}
      </p>
    </template>
  </article>
</template>
