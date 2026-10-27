"""Abordagem 1 (linha de base): questionário adaptativo por árvore de decisão.

IDEIA (inspirada em Ortigosa, Paredes e Rodríguez, 2010):
uma árvore de decisão treinada para prever o polo de uma dimensão a partir
das respostas JÁ É um questionário adaptativo:
  - a raiz é a primeira pergunta feita a todos;
  - conforme a resposta (a/b), desce para um filho, que é a próxima pergunta;
  - ao chegar numa folha, o questionário daquela dimensão para, e a folha
    diz o polo previsto.
Então o número de perguntas feitas a um aluno é o comprimento do caminho
da raiz até a folha dele. Limitando a profundidade da árvore, trocamos
acurácia por menos perguntas — é isso que gera a curva acurácia × nº de questões.

Como as respostas são binárias, um item nunca se repete num mesmo caminho
(depois de perguntado, ele vale sempre 0 ou sempre 1 naquele ramo), então
"profundidade da folha" = "nº de questões feitas".

Detalhe importante para a banca: para ter CERTEZA do polo, o ILS precisa de
pelo menos 6 respostas iguais numa dimensão (6 de 11 já decidem o sinal).
Qualquer questionário com menos de 6 perguntas por dimensão está apostando;
a árvore aposta com base na estatística dos dados de treino.

Duas variantes (config `itens_entrada`):
  - "dimensao": a árvore da dimensão d só pode perguntar os 11 itens de d
    (variante clássica);
  - "todos": pode perguntar qualquer um dos 44 itens. Como sensorial/intuitivo
    e sequencial/global são correlacionados, um item de uma pode ajudar a
    outra. Nesse caso o total de questões é contado SEM repetição.
"""

from dataclasses import dataclass, field

import numpy as np
from sklearn.tree import DecisionTreeClassifier, export_text

from .constantes import COLUNAS_ITENS, DIMENSOES, N_DIMENSOES, N_ITENS, itens_da_dimensao


@dataclass
class QuestionarioArvore:
    profundidades: list[int]                 # profundidade máxima de cada dimensão
    itens_entrada: str = "dimensao"          # "dimensao" | "todos"
    criterio: str = "entropy"                # "entropy" (ganho de informação, como no C4.5) | "gini"
    min_amostras_folha: int = 20
    seed: int = 0
    arvores: list = field(default_factory=list, init=False)
    colunas: list = field(default_factory=list, init=False)        # índices (0..43) usados por dimensão
    intensidade_folha: list = field(default_factory=list, init=False)

    def _colunas_dimensao(self, d: int) -> list[int]:
        if self.itens_entrada == "dimensao":
            return [i - 1 for i in itens_da_dimensao(d)]
        if self.itens_entrada == "todos":
            return list(range(N_ITENS))
        raise ValueError("itens_entrada deve ser 'dimensao' ou 'todos'")

    def treinar(self, X: np.ndarray, polo: np.ndarray, intensidade: np.ndarray) -> "QuestionarioArvore":
        """X: (n, 44) respostas; polo e intensidade: (n, 4) do gabarito."""
        self.arvores, self.colunas, self.intensidade_folha = [], [], []
        for d in range(N_DIMENSOES):
            cols = self._colunas_dimensao(d)
            arvore = DecisionTreeClassifier(
                criterion=self.criterio,
                max_depth=self.profundidades[d],
                min_samples_leaf=self.min_amostras_folha,
                random_state=self.seed,
            ).fit(X[:, cols], polo[:, d])

            # Intensidade prevista em cada folha: a faixa mais comum entre os
            # alunos de treino que caíram nessa folha e têm o polo que a folha prevê.
            # Assim a intensidade sai das MESMAS perguntas, sem perguntas extras.
            folhas = arvore.apply(X[:, cols])
            polo_folha = arvore.predict(X[:, cols])
            mapa = {}
            for f in np.unique(folhas):
                sel = (folhas == f) & (polo[:, d] == polo_folha[folhas == f][0])
                valores = intensidade[sel, d] if sel.any() else intensidade[folhas == f, d]
                mapa[int(f)] = int(np.bincount(valores).argmax())

            self.arvores.append(arvore)
            self.colunas.append(cols)
            self.intensidade_folha.append(mapa)
        return self

    def prever(self, X: np.ndarray) -> dict[str, np.ndarray]:
        """Simula o questionário para cada respondente de X.

        Retorna:
          polo, intensidade : (n, 4) previstos
          n_questoes        : (n, 4) perguntas feitas pela árvore de cada dimensão
          n_total           : (n,)   perguntas DISTINTAS feitas no total
          perguntados       : (n, 44) máscara booleana dos itens perguntados
        """
        n = X.shape[0]
        polo = np.empty((n, N_DIMENSOES), dtype=np.int8)
        intens = np.empty((n, N_DIMENSOES), dtype=np.int8)
        n_q = np.empty((n, N_DIMENSOES), dtype=np.int16)
        perguntados = np.zeros((n, N_ITENS), dtype=bool)

        for d, (arvore, cols, mapa) in enumerate(zip(self.arvores, self.colunas, self.intensidade_folha)):
            Xd = X[:, cols]
            polo[:, d] = arvore.predict(Xd)
            intens[:, d] = [mapa[int(f)] for f in arvore.apply(Xd)]

            # decision_path marca os nós visitados; os nós internos visitados são as perguntas
            caminho = arvore.decision_path(Xd).toarray().astype(bool)
            internos = arvore.tree_.children_left != -1
            feito = caminho & internos[None, :]
            n_q[:, d] = feito.sum(axis=1)
            feature_no = arvore.tree_.feature
            for no in np.where(internos)[0]:
                perguntados[feito[:, no], cols[feature_no[no]]] = True

        return {"polo": polo, "intensidade": intens, "n_questoes": n_q,
                "n_total": perguntados.sum(axis=1), "perguntados": perguntados}

    def proxima_questao(self, d: int, respostas: dict[int, int]) -> tuple[int | None, int | None]:
        """Percorre a árvore da dimensão d com as respostas já dadas.

        respostas: {numero_do_item (1..44): 0 ou 1}
        Retorna (próximo item a perguntar, None) ou (None, polo previsto).
        É a função que o backend da plataforma vai usar, uma pergunta por vez.
        """
        arv = self.arvores[d].tree_
        no = 0
        while arv.children_left[no] != -1:
            item = self.colunas[d][arv.feature[no]] + 1
            if item not in respostas:
                return item, None
            # sklearn: vai para a esquerda se valor <= limiar (0,5) → resposta "b" (0)
            no = arv.children_left[no] if respostas[item] <= arv.threshold[no] else arv.children_right[no]
        return None, int(self.arvores[d].classes_[np.argmax(arv.value[no])])

    def texto(self) -> str:
        """Árvores em texto legível, com os nomes dos itens (q01..q44), para o apêndice."""
        partes = []
        for d, (arvore, cols) in enumerate(zip(self.arvores, self.colunas)):
            nomes = [COLUNAS_ITENS[c] for c in cols]
            partes.append(f"=== {DIMENSOES[d]} (profundidade máx. {self.profundidades[d]}) ===\n"
                          f"(qXX <= 0.50 significa resposta 'b'; classe 1 = polo da resposta 'a')\n"
                          + export_text(arvore, feature_names=nomes))
        return "\n".join(partes)
