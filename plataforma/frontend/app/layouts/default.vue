<!-- Moldura das páginas logadas: menu lateral no computador, barra inferior no celular. -->
<script setup lang="ts">
const route = useRoute()
const sessao = useSessao()

const itens = [
  { para: '/', rotulo: 'Início', icone: 'inicio' as const },
  { para: '/salas', rotulo: 'Salas', icone: 'salas' as const },
  { para: '/conta', rotulo: 'Conta', icone: 'conta' as const },
]

function ativo(para: string) {
  return para === '/' ? route.path === '/' : route.path.startsWith(para)
}
</script>

<template>
  <div class="min-h-dvh papel-quadriculado md:flex">
    <!-- menu lateral (computador) -->
    <aside class="hidden md:flex md:w-60 md:shrink-0 md:flex-col md:border-r md:border-linha md:bg-white md:px-5 md:py-6">
      <NuxtLink to="/" class="no-underline" aria-label="MatIF, início"><Logo /></NuxtLink>
      <nav class="mt-10 flex flex-col gap-1" aria-label="Principal">
        <NuxtLink
          v-for="item in itens" :key="item.para" :to="item.para"
          class="flex items-center gap-3 rounded-lg px-3 py-2.5 no-underline transition-colors"
          :class="ativo(item.para) ? 'bg-caneta/10 font-medium text-caneta' : 'text-tinta-suave hover:bg-papel hover:text-tinta'"
          :aria-current="ativo(item.para) ? 'page' : undefined"
        >
          <Icone :nome="item.icone" /> {{ item.rotulo }}
        </NuxtLink>
      </nav>
      <div class="mt-auto border-t border-linha pt-4">
        <p class="truncate text-sm font-medium">{{ sessao.usuario.value?.nome }}</p>
        <p class="text-sm text-tinta-suave">{{ sessao.ehProfessor.value ? 'Professor' : 'Aluno' }}</p>
        <button type="button" class="mt-3 flex items-center gap-2 text-sm text-tinta-suave hover:text-tinta" @click="sessao.sair()">
          <Icone nome="sair" /> Sair
        </button>
      </div>
    </aside>

    <!-- conteúdo -->
    <main class="mx-auto w-full max-w-4xl px-4 pb-28 pt-6 md:px-10 md:pb-12 md:pt-10">
      <div class="mb-6 md:hidden"><NuxtLink to="/" class="no-underline" aria-label="MatIF, início"><Logo /></NuxtLink></div>
      <slot />
    </main>

    <!-- barra inferior (celular) -->
    <nav class="fixed inset-x-0 bottom-0 z-10 grid grid-cols-3 border-t border-linha bg-white pb-[env(safe-area-inset-bottom)] md:hidden" aria-label="Principal">
      <NuxtLink
        v-for="item in itens" :key="item.para" :to="item.para"
        class="flex flex-col items-center gap-0.5 py-2.5 text-xs no-underline"
        :class="ativo(item.para) ? 'font-medium text-caneta' : 'text-tinta-suave'"
        :aria-current="ativo(item.para) ? 'page' : undefined"
      >
        <Icone :nome="item.icone" /> {{ item.rotulo }}
      </NuxtLink>
    </nav>
  </div>
</template>
