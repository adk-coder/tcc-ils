<!-- Resultado do questionário de estilos, pensado para o aluno do 9º ano:
     1. o PERFIL em uma frase (o que ele precisa guardar);
     2. como estudar no MatIF (as 4 dicas juntas);
     3. cada parte explicada, só com o estilo dele (o oposto aparece como lembrete, não como opção);
     4. os números da IA ficam guardados em "Como a IA chegou nesse resultado". -->
<script setup lang="ts">
import type { Dimensao, DimensaoEstilo, ItemRespondido } from '~/utils/tipos'
import { DIMENSOES, POLOS, frasePerfil } from '~/utils/estilos'

const props = defineProps<{
  resultado: DimensaoEstilo[]
  respondidas: number
  itensRespondidos?: ItemRespondido[] | null
}>()

const polos = computed(() => props.resultado.map(d => d.polo))
const frase = computed(() => frasePerfil(polos.value))

function porcentagem(x: number) { return `${Math.round(100 * x)}%` }

function polosDaDimensao(d: Dimensao): string {
  return DIMENSOES[d]?.polos.join('/') ?? d
}
</script>

<template>
  <div class="flex flex-col gap-8">
    <!-- 1. perfil -->
    <section class="folha-caderno flex flex-col gap-4" aria-labelledby="titulo-perfil">
      <h2 id="titulo-perfil" class="text-sm font-medium uppercase tracking-wide text-caneta">Seu perfil</h2>
      <p class="flex flex-wrap gap-2">
        <span v-for="p in polos" :key="p"
              class="rounded-full bg-marca/50 px-3.5 py-1 font-display text-lg font-extrabold">{{ POLOS[p]?.nome }}</span>
      </p>
      <p class="text-xl leading-snug sm:text-2xl">
        Sua preferência é aprender <strong class="font-semibold"><span class="marca-texto">{{ frase }}</span></strong>.
      </p>
    </section>

    <!-- 2. como estudar -->
    <section class="flex flex-col gap-3" aria-labelledby="titulo-dicas">
      <h2 id="titulo-dicas" class="text-xl">Como estudar no MatIF</h2>
      <ul class="folha divide-y divide-linha">
        <li v-for="d in resultado" :key="d.dimensao" class="flex flex-col divide-y divide-linha px-5">
          <!-- para aproveitar a preferência -->
          <div class="flex gap-3 py-3.5">
            <Icone nome="certo" class="mt-0.5 shrink-0 text-acerto" />
            <div class="flex flex-col gap-0.5">
              <span class="text-xs text-tinta-suave">Para aproveitar sua preferência</span>
              <span>{{ POLOS[d.polo]?.dica }}</span>
            </div>
          </div>
          <!-- para desenvolver o outro lado -->
          <div class="flex gap-3 py-3.5">
            <Icone nome="certo" class="mt-0.5 shrink-0 text-caneta" />
            <div class="flex flex-col gap-0.5">
              <span class="text-xs text-tinta-suave">Para desenvolver o lado {{ POLOS[d.polo_oposto]?.nome.toLowerCase() }}</span>
              <span>{{ POLOS[d.polo]?.dica_outro_lado }}</span>
            </div>
          </div>
        </li>
      </ul>
    </section>

    <!-- 3. cada parte -->
    <section class="flex flex-col gap-3" aria-labelledby="titulo-partes">
      <h2 id="titulo-partes" class="text-xl">Entenda cada parte</h2>
      <div class="grid gap-3 sm:grid-cols-2">
        <article v-for="d in resultado" :key="d.dimensao" class="folha flex flex-col gap-2 p-5">
          <p class="text-sm text-tinta-suave">{{ DIMENSOES[d.dimensao].pergunta }}</p>
          <h3 class="text-xl"><span class="marca-texto">{{ POLOS[d.polo]?.nome }}</span></h3>
          <p>{{ POLOS[d.polo]?.descricao }}</p>
          <p class="mt-auto pt-1 text-sm text-tinta-suave">
            O outro lado é o estilo <strong>{{ POLOS[d.polo_oposto]?.nome.toLowerCase() }}</strong>.
            Todo mundo usa um pouco dos dois.
          </p>
        </article>
      </div>
    </section>

    <!-- 4. transparência da IA (fechado por padrão) -->
    <details class="folha group p-5">
      <summary class="cursor-pointer list-none font-medium text-caneta [&::-webkit-details-marker]:hidden">
        <span class="inline-block transition-transform group-open:rotate-90" aria-hidden="true">›</span>
        Como a IA chegou nesse resultado?
      </summary>
      <div class="mt-3 flex flex-col gap-3 text-sm">
        <p>
          O questionário completo tem 44 perguntas. Em cada parte, a inteligência artificial escolheu
          as perguntas mais úteis para você e parou quando ficou segura de que as 44 dariam o mesmo resultado.
        </p>
        <table class="w-full text-left">
          <thead class="text-tinta-suave">
            <tr><th class="py-1 font-normal">Parte</th><th class="py-1 font-normal">Perguntas</th><th class="py-1 font-normal">Segurança</th></tr>
          </thead>
          <tbody>
            <tr v-for="d in resultado" :key="d.dimensao" class="border-t border-linha">
              <td class="py-1.5">{{ POLOS[d.polo]?.nome }}</td>
              <td class="py-1.5">{{ d.n_questoes }}</td>
              <td class="py-1.5">{{ porcentagem(d.confianca) }}</td>
            </tr>
          </tbody>
        </table>
        <p class="text-tinta-suave">
          "Segurança" é a chance, calculada pela IA, de o questionário completo dar o mesmo estilo nessa parte.
        </p>

        <template v-if="itensRespondidos?.length">
          <h3 class="font-medium">Perguntas que a IA escolheu</h3>
          <ol class="flex flex-col">
            <li v-for="ir in itensRespondidos" :key="ir.numero"
                class="flex gap-3 border-t border-linha py-2">
              <span class="w-6 shrink-0 font-display font-semibold text-caneta">{{ ir.numero }}ª</span>
              <div class="min-w-0">
                <p class="text-xs text-tinta-suave">Item {{ ir.item }} · {{ polosDaDimensao(ir.dimensao) }}</p>
                <p class="mt-0.5 italic">{{ ir.enunciado }}</p>
              </div>
            </li>
          </ol>
          <p class="text-tinta-suave">
            Você respondeu <strong class="text-tinta">{{ respondidas }}</strong> de 44 perguntas.
            A IA parou cada parte quando já tinha segurança suficiente sobre o resultado.
          </p>
        </template>
      </div>
    </details>
  </div>
</template>
