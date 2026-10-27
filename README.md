# TCC — Questionário adaptativo do ILS + plataforma de matemática

Augusto Dorador Kawashima — Ciência da Computação, IFC Campus Videira
Orientador: Prof. Dr. Rafael Antonio Zanin · Coorientador: Prof. Dr. Manasses Ribeiro

## Organização

```
tcc-ils/
├── ia/                         # tudo que é aprendizado de máquina (Python)
│   ├── configs/                # parâmetros em YAML (nada "mágico" dentro do código)
│   │   ├── itens_ils.yaml      # parâmetros dos 44 itens (correlações, proporções)
│   │   └── gerador.yaml        # tamanho da base, seed, divisão, traço latente
│   ├── src/ils_adaptativo/     # pacote com o código reutilizável
│   │   ├── constantes.py       # dimensões, mapeamento item → dimensão
│   │   ├── escore.py           # escore, polo e intensidade do ILS
│   │   ├── irt.py              # funções do modelo 2PL
│   │   ├── calibracao.py       # transforma correlações publicadas em a_i, b_i
│   │   ├── gerador.py          # gera os respondentes sintéticos
│   │   └── registro.py         # registro de experimentos (parâmetros + resultados)
│   ├── scripts/                # pontos de entrada executáveis (um por etapa)
│   │   └── gerar_base.py
│   ├── testes/                 # testes automáticos (pytest)
│   ├── notebooks/              # exploração e gráficos (não é código "oficial")
│   ├── dados/                  # NÃO versionado (ver .gitignore)
│   │   ├── bruto/              # base pública real, se for encontrada
│   │   └── sintetico/          # treino / validacao / teste em parquet
│   └── experimentos/           # um diretório por execução + registro.csv
├── plataforma/
│   ├── backend/                # FastAPI + SQLModel + PostgreSQL
│   └── frontend/               # Nuxt 3 (PWA)
└── docs/                       # decisões de projeto (alimentam o texto do TCC)
```

Regra geral: **todo resultado que vai para o texto sai de `ia/experimentos/`**, e todo
experimento é reproduzível a partir da config + seed registrada.

## Ambiente Python (ia/)

```bash
cd ia
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cpu   # PyTorch só CPU (menor)
pip install -r requirements.txt
pip install -e .                   # instala o pacote ils_adaptativo em modo edição
python scripts/verificar_ambiente.py
pip freeze > requirements-lock.txt # congela as versões EXATAS usadas no TCC
pytest testes/
```

## Etapa 1 — gerar a base sintética

```bash
cd ia
python scripts/gerar_base.py --config configs/gerador.yaml
```

## Etapa 2 — linha de base (árvore de decisão)

```bash
cd ia
python scripts/treinar_arvore.py --config configs/arvore.yaml
```

Gera a curva acurácia × nº de questões (`curva_arvore.png`), as árvores em texto
para o apêndice e as métricas no teste, junto da referência sem IA (parada garantida).

## Etapa 3 — TAC clássico com TRI

```bash
cd ia
python scripts/treinar_tac.py --config configs/tac.yaml
```

Estima o 2PL com girth, simula o TAC (máxima informação de Fisher) para vários
limiares de parada e gera `curva_tac.png` comparando TAC, árvore e parada garantida.
Rode a etapa 2 antes para a curva da árvore aparecer no gráfico. Leva alguns minutos.

## Etapa 4a — classificador de respostas parciais (MLP, PyTorch)

```bash
cd ia
python scripts/treinar_classificador.py --config configs/classificador.yaml
```

Treina o MLP que prevê o polo das 4 dimensões a partir de respostas parciais e
compara com a probabilidade da TRI (`curva_classificador.png`). É a peça que dá o
resultado final quando a política de RL encerra o questionário.

## Etapa 4b — política de seleção (MaskablePPO)

```bash
cd ia
python scripts/treinar_rl.py --rapido   # conferência em poucos minutos (não usa o teste)
python scripts/treinar_rl.py            # experimento completo: pode levar horas em CPU
```

No Windows, para ver o progresso ao vivo e guardar o log (PowerShell):

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
python -u -X utf8 scripts/treinar_rl.py 2>&1 | Tee-Object -FilePath rl_completo.log
```

Usa o classificador mais recente da etapa 4a. Treina uma política por λ, escolhe o λ
pela validação, avalia no teste e gera `curva_rl.png` (RL × TAC).
