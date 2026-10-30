<!-- "Meus adesivos": as conquistas do aluno, como figurinhas coladas no caderno.
     Premiam o progresso de cada um (não comparam com os colegas, como o ranking). -->
<script setup lang="ts">
useHead({ title: 'Meus adesivos — MatIF' })
const sessao = useSessao()
if (sessao.ehProfessor.value) await navigateTo('/')

const { verificar } = useConquistas()
const { data: adesivos } = await useAsyncData('adesivos', () => verificar(), { default: () => [] })
const ganhos = computed(() => (adesivos.value ?? []).filter(a => a.ganho).length)

function data(iso: string | null) {
  if (!iso) return ''
  return new Date(/Z|[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`).toLocaleDateString('pt-BR')
}
</script>

<template>
  <div class="flex flex-col gap-8">
    <header>
      <h1 class="text-3xl md:text-4xl">Meus adesivos</h1>
      <p class="mt-1 text-tinta-suave">
        Você já colou <strong class="font-display text-tinta"><span class="marca-texto">{{ ganhos }} de {{ adesivos?.length ?? 0 }}</span></strong>
        adesivos no seu caderno.
      </p>
    </header>

    <ul class="folha-caderno grid grid-cols-2 gap-x-4 gap-y-8 sm:grid-cols-4">
      <li v-for="(a, i) in adesivos ?? []" :key="a.id" class="flex flex-col items-center gap-2 text-center">
        <Adesivo :adesivo="a" :indice="i" />
        <p class="font-display font-semibold leading-tight" :class="!a.ganho && 'text-tinta-suave'">{{ a.titulo }}</p>
        <p v-if="a.ganho" class="text-xs text-tinta-suave">colado em {{ data(a.ganho_em) }}</p>
        <template v-else>
          <p class="text-xs text-tinta-suave">{{ a.descricao }}</p>
          <p v-if="a.meta > 1" class="text-xs font-medium text-caneta">{{ a.progresso }}/{{ a.meta }}</p>
        </template>
      </li>
    </ul>

    <p class="text-sm text-tinta-suave">
      Os adesivos medem o seu progresso, não a comparação com os colegas. Cada um no seu ritmo.
    </p>
  </div>
</template>
