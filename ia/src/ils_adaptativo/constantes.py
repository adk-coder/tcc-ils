"""Constantes do Index of Learning Styles (ILS).

O ILS tem 44 itens. Eles se alternam entre as 4 dimensões em ciclo:
    item 1 → ativo/reflexivo, item 2 → sensorial/intuitivo,
    item 3 → visual/verbal,   item 4 → sequencial/global,
    item 5 → ativo/reflexivo, ... e assim por diante até o item 44.
Logo, cada dimensão tem 11 itens, e o item i (1..44) pertence à dimensão (i-1) % 4.

Convenção de sinal (a mesma do instrumento): a resposta "a" conta para o
PRIMEIRO polo do nome da dimensão (ativo, sensorial, visual, sequencial) e a
resposta "b" para o segundo. Nesta base, resposta "a" é codificada como 1 e
"b" como 0.
"""

N_ITENS = 44
N_DIMENSOES = 4
ITENS_POR_DIMENSAO = 11

# Nomes curtos usados em colunas de arquivos e no código
DIMENSOES = ["ati_ref", "sen_int", "vis_ver", "seq_glo"]

# Nome de cada polo: (polo da resposta "a", polo da resposta "b")
POLOS = {
    "ati_ref": ("ativo", "reflexivo"),
    "sen_int": ("sensorial", "intuitivo"),
    "vis_ver": ("visual", "verbal"),
    "seq_glo": ("sequencial", "global"),
}


def dimensao_do_item(item: int) -> int:
    """Índice da dimensão (0..3) de um item numerado de 1 a 44."""
    if not 1 <= item <= N_ITENS:
        raise ValueError(f"item deve estar entre 1 e {N_ITENS}, recebido {item}")
    return (item - 1) % N_DIMENSOES


def itens_da_dimensao(d: int) -> list[int]:
    """Lista dos itens (numerados 1..44) que pertencem à dimensão d (0..3)."""
    return [i for i in range(1, N_ITENS + 1) if dimensao_do_item(i) == d]


# Colunas das respostas no arquivo: q01, q02, ..., q44
COLUNAS_ITENS = [f"q{i:02d}" for i in range(1, N_ITENS + 1)]
