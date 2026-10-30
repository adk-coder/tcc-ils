<script setup lang="ts">
import type { Sala } from '~/utils/tipos'

useHead({ title: 'Salas — MatIF' })
const sessao = useSessao()
const api = useApi()
const professor = sessao.ehProfessor
const { data: salas, refresh } = await useAsyncData('salas', () => api<Sala[]>('/salas'), { default: () => [] })
</script>

<template>
  <div class="flex flex-col gap-8">
    <h1 class="text-3xl">Salas</h1>

    <section class="folha p-5 sm:p-6">
      <h2 class="mb-4 text-lg">{{ professor ? 'Criar uma sala' : 'Entrar em uma sala' }}</h2>
      <FormCriarSala v-if="professor" @feito="refresh()" />
      <FormEntrarSala v-else @feito="refresh()" />
    </section>

    <section class="flex flex-col gap-4">
      <h2 class="text-xl">{{ professor ? 'Suas salas' : 'Salas em que você está' }}</h2>
      <div v-if="salas.length" class="grid gap-3 sm:grid-cols-2">
        <CartaoSala v-for="s in salas" :key="s.id" :sala="s" :professor="professor" />
      </div>
      <p v-else class="text-tinta-suave">Nenhuma sala ainda.</p>
    </section>
  </div>
</template>
