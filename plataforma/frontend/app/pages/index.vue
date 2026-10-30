<!-- Início: o que fazer agora. Aluno vê o próprio progresso; professor vê as salas. -->
<script setup lang="ts">
import type { EstadoEstilo, Progresso, Sala } from '~/utils/tipos'
import { POLOS } from '~/utils/estilos'

useHead({ title: 'Início — MatIF' })
const sessao = useSessao()
const api = useApi()
const professor = sessao.ehProfessor

const { data: salas, refresh } = await useAsyncData('inicio-salas', () => api<Sala[]>('/salas'), { default: () => [] })
const { data: progresso } = await useAsyncData('inicio-progresso',
  () => (professor.value ? Promise.resolve(null) : api<Progresso>('/eu/progresso')))
// questionário de estilos: se der erro (ex.: modelo ainda não exportado), o cartão só não aparece
const { data: estilo } = await useAsyncData('inicio-estilo',
  () => (professor.value ? Promise.resolve(null) : api<EstadoEstilo>('/eu/estilo').catch(() => null)))
</script>

<template>
  <div class="flex flex-col gap-8">
    <header>
      <h1 class="text-3xl md:text-4xl">Oi, {{ sessao.primeiroNome.value }}</h1>
      <p class="mt-1 text-tinta-suave">
        {{ professor ? 'Acompanhe suas turmas e prepare os próximos módulos.' : 'Bora continuar de onde você parou?' }}
      </p>
    </header>

    <!-- progresso do aluno -->
    <section v-if="!professor && progresso" class="folha grid grid-cols-3 divide-x divide-linha" aria-label="Seu progresso">
      <div class="p-4 text-center sm:p-5">
        <p class="font-display text-3xl font-extrabold sm:text-4xl"><span class="marca-texto">{{ progresso.pontos }}</span></p>
        <p class="mt-1 text-sm text-tinta-suave">pontos</p>
      </div>
      <div class="p-4 text-center sm:p-5">
        <p class="font-display text-3xl font-extrabold sm:text-4xl">{{ progresso.streak_atual }}</p>
        <p class="mt-1 text-sm text-tinta-suave">{{ progresso.streak_atual === 1 ? 'dia seguido' : 'dias seguidos' }}</p>
      </div>
      <div class="p-4 text-center sm:p-5">
        <p class="font-display text-3xl font-extrabold sm:text-4xl">{{ progresso.exercicios_acertados }}</p>
        <p class="mt-1 text-sm text-tinta-suave">exercícios certos</p>
      </div>
    </section>

    <!-- questionário de estilos: convite (ou atalho para o resultado) -->
    <NuxtLink v-if="!professor && estilo" to="/estilo"
              class="folha flex items-center gap-4 p-5 text-tinta no-underline transition-colors hover:border-caneta sm:p-6">
      <span class="grid size-12 shrink-0 place-items-center rounded-full bg-marca/40 text-tinta">
        <Icone nome="estilo" />
      </span>
      <span class="min-w-0 flex-1">
        <template v-if="estilo.status === 'concluido' && estilo.resultado">
          <span class="block font-display text-lg font-semibold">Seu estilo de aprendizagem</span>
          <span class="text-sm text-tinta-suave">{{ estilo.resultado.map(d => POLOS[d.polo]?.nome).join(' · ') }}</span>
        </template>
        <template v-else>
          <span class="block font-display text-lg font-semibold">
            {{ estilo.status === 'em_andamento' ? 'Continue o questionário' : 'Descubra como você aprende melhor' }}
          </span>
          <span class="text-sm text-tinta-suave">Poucas perguntas, sem resposta certa ou errada.</span>
        </template>
      </span>
      <span class="hidden shrink-0 text-sm font-medium text-caneta sm:block">
        {{ estilo.status === 'concluido' ? 'Ver' : estilo.status === 'em_andamento' ? 'Continuar' : 'Começar' }}
      </span>
    </NuxtLink>

    <section class="flex flex-col gap-4">
      <h2 class="text-xl">Suas salas</h2>
      <div v-if="salas.length" class="grid gap-3 sm:grid-cols-2">
        <CartaoSala v-for="s in salas" :key="s.id" :sala="s" :professor="professor" />
      </div>
      <div v-else class="folha p-5 sm:p-6">
        <p class="mb-4">
          {{ professor
            ? 'Você ainda não criou nenhuma sala. Crie a primeira e passe o código para seus alunos.'
            : 'Você ainda não está em nenhuma sala. Digite o código que seu professor passou.' }}
        </p>
        <FormCriarSala v-if="professor" @feito="refresh()" />
        <FormEntrarSala v-else @feito="refresh()" />
      </div>
    </section>
  </div>
</template>
