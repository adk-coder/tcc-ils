"""Textos dos 44 itens do ILS (enunciado e alternativas "a" e "b").

Os textos ficam em itens.json, separados do código. ATENÇÃO: o arquivo do repositório
vem com textos PROVISÓRIOS (status "PROVISORIO"). Antes do uso com alunos, substitua
pela versão em português adotada no TCC (com a referência em "fonte") e mude o status
para "OFICIAL". Os textos não foram inventados aqui de propósito: o instrumento precisa
ser o publicado, para o resultado ser comparável ao do ILS.
"""

import json
from functools import lru_cache
from pathlib import Path

CAMINHO = Path(__file__).with_name("itens.json")


@lru_cache
def _carregar() -> tuple[str, dict[int, dict]]:
    dados = json.loads(CAMINHO.read_text(encoding="utf-8"))
    itens = {int(i["item"]): i for i in dados["itens"]}
    if sorted(itens) != list(range(1, 45)):
        raise ValueError("itens.json precisa ter exatamente os itens 1 a 44")
    return dados.get("status", "PROVISORIO"), itens


def textos_provisorios() -> bool:
    return _carregar()[0] != "OFICIAL"


def texto_do_item(item: int) -> dict:
    """{"item": n, "enunciado": ..., "a": ..., "b": ...}"""
    return _carregar()[1][item]
