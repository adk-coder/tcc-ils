// Adesivos de conquista: busca a lista na API e, se apareceu um adesivo NOVO desde a
// última consulta, deixa-o em `novo` (o aviso do layout mostra "Novo adesivo!").
// A 1ª consulta da sessão só serve de referência: não avisa o que já tinha sido ganho.
import type { Adesivo } from '~/utils/tipos'

export function useConquistas() {
  const api = useApi()
  const conhecidos = useState<string[] | null>('adesivos-conhecidos', () => null)
  const novo = useState<Adesivo | null>('adesivo-novo', () => null)

  async function verificar(): Promise<Adesivo[] | null> {
    try {
      const lista = await api<Adesivo[]>('/eu/conquistas')
      const ganhos = lista.filter(a => a.ganho)
      if (conhecidos.value !== null) {
        const recente = ganhos.find(a => !conhecidos.value!.includes(a.id))
        if (recente) novo.value = recente
      }
      conhecidos.value = ganhos.map(a => a.id)
      return lista
    } catch {
      return null      // adesivos são um extra: se falhar, o resto do app segue normal
    }
  }

  return { verificar, novo }
}
