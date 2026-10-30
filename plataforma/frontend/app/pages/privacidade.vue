<!-- Texto provisório: revisar com o orientador antes do uso com alunos reais. -->
<script setup lang="ts">
definePageMeta({ layout: 'publico' })
useHead({ title: 'Privacidade — MatIF' })
</script>

<template>
  <article class="folha flex flex-col gap-4 p-6 text-[0.95rem] sm:p-8">
    <h1 class="text-2xl">Termos de uso e privacidade</h1>
    <p>O MatIF é uma plataforma de reforço de matemática desenvolvida como Trabalho de Conclusão de Curso no Instituto Federal Catarinense, Campus Videira.</p>
    <h2 class="text-lg">Quais dados guardamos</h2>
    <p>Somente seu nome, seu e-mail, sua senha (guardada de forma cifrada, nunca em texto) e as respostas que você der aos exercícios. Não pedimos CPF, data de nascimento, endereço nem telefone.</p>
    <h2 class="text-lg">Questionário de estilos de aprendizagem</h2>
    <p>Se você responder o questionário "Meu estilo", guardamos suas respostas e o resultado, para você poder parar e continuar depois e rever o resultado. Só você vê o seu resultado. Você pode refazer o questionário (o anterior é apagado), baixar esses dados ou apagá-los junto com a conta.</p>
    <h2 class="text-lg">Para que usamos</h2>
    <p>Para você entrar na plataforma, participar das salas do seu professor, corrigir seus exercícios e mostrar seu progresso. Seus dados não são vendidos nem compartilhados.</p>
    <h2 class="text-lg">Quem vê o quê</h2>
    <p>Seu professor vê seu nome e seu desempenho nas salas dele. Seus colegas veem apenas seu primeiro nome e a inicial do sobrenome no ranking da sala.</p>
    <h2 class="text-lg">Seus direitos</h2>
    <p>Na página Conta você pode baixar todos os seus dados e excluir sua conta a qualquer momento. A exclusão apaga também suas respostas.</p>
    <NuxtLink to="/cadastro" class="mt-2 text-sm">Voltar para o cadastro</NuxtLink>
  </article>
</template>
