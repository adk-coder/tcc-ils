<!-- Círculo "feito à caneta" que se desenha em volta de uma letra (ver .traco-caneta em main.css).
     Coloque dentro de um elemento com position: relative. A cor vem de text-* (currentColor). -->
<template>
  <svg viewBox="0 0 48 48" fill="none" aria-hidden="true"
       class="pointer-events-none absolute left-1/2 top-1/2 size-12 -translate-x-1/2 -translate-y-1/2">
    <path class="traco-caneta" pathLength="1" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"
          d="M31 7.5C18 3.5 6 12 6.5 25c.5 12.5 13.5 19.5 26 15C43.5 36 45 19.5 36.5 11.5 32 7.5 25 6 19 8.5" />
  </svg>
</template>
