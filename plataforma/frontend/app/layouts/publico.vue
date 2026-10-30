<!-- Moldura das páginas sem login (entrar, cadastro, privacidade). -->
<template>
  <div class="min-h-dvh papel-quadriculado px-4 py-10">
    <div class="mx-auto w-full max-w-md">
      <div class="mb-8 text-center">
        <Logo tamanho="g" />
        <p class="mt-3 text-tinta-suave">Reforço de matemática para o Partiu IF</p>
      </div>
      <slot />
    </div>
  </div>
</template>
