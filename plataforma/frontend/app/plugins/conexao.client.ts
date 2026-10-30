// Acompanha se o aparelho está com internet. O layout mostra um aviso quando cai,
// porque o app abre offline (PWA), mas os dados vêm da API.
export default defineNuxtPlugin(() => {
  const online = useState('online', () => navigator.onLine)
  window.addEventListener('online', () => (online.value = true))
  window.addEventListener('offline', () => (online.value = false))
})
