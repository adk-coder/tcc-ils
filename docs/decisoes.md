# Registro de decisões de projeto

Cada decisão tem: o que foi decidido, por quê, e o que fica como limitação.
Serve de rascunho para o capítulo de Desenvolvimento e de "cola" para a banca.

## D1 — Separar `ia/` e `plataforma/` no mesmo repositório
Os dois lados têm ciclos diferentes (experimentos × sistema em produção), mas
o modelo treinado em `ia/` será consumido pelo backend. Um repositório só
mantém o histórico junto; pastas separadas evitam misturar dependências.

## D2 — Python 3.11
Versão com amplo suporte de wheels para PyTorch e Stable-Baselines3.
As versões exatas ficam congeladas em `ia/requirements-lock.txt` e também
são gravadas automaticamente em `ambiente.json` de cada experimento.

## D3 — Uma seed "mãe" com fluxos independentes
`SeedSequence(seed).spawn(4)` gera 4 geradores independentes: calibração,
traços latentes, respostas e divisão. Mudar um passo (ex.: tamanho da amostra
de calibração) não altera os sorteios dos outros. A execução é verificada como
reproduzível: rodar duas vezes gera arquivos com o mesmo hash SHA-256.

## D4 — Calibração por simulação, não só por fórmula
A literatura publica estatísticas clássicas, não parâmetros a_i, b_i. Os
valores por item vêm da Tabela 3 de Litzinger, Lee, Wise e Felder (2005,
ASEE): correlação item-total CORRIGIDA dos 44 itens, N = 572. O artigo de
Felder e Spurlin (2005) não traz valores por item; ele é usado para a
correlação entre escalas (D9). A conversão por fórmula (modelo de variável latente) é
só um chute inicial; o ajuste por simulação garante que a base reproduz as
correlações publicadas (tabela `itens_calibrados.csv`: r_alvo × r_obtido).

## D5 — θ padronizado e p_i = 0,5
θ ~ Normal(0, 1) em cada dimensão; a tendência da população a um polo entraria
pelas proporções p_i (que definem b_i). Nenhum artigo encontrado publica p_i
por item, e as distribuições de preferência publicadas são de estudantes de
engenharia, não do 9º ano. Usamos p_i = 0,5 (polos equilibrados), declarado
como limitação.

## D6 — Gabarito = ILS completo, não θ
O objetivo é reproduzir o resultado das 44 questões. θ é salvo apenas com o
prefixo `oculto_` para análise de erros e nunca entra nos modelos.

## D7 — Divisão 70/15/15 antes de qualquer modelagem
Embaralhamento aleatório com fluxo próprio; os arquivos de treino, validação
e teste são gravados separadamente. O teste só é usado na avaliação final.

## D8 — Item 40 com correlação negativa
Litzinger et al. reportam r = −0,0105 para o item 40 (praticamente zero). Um
2PL com a > 0 não gera correlação negativa; o item é modelado com
r_minimo = 0,02, ou seja, quase aleatório. O item também aparece marcado
na análise fatorial do artigo (Tabela 5).

## D9 — Correlação entre sensorial/intuitivo e sequencial/global
Felder e Spurlin (2005) relatam correlação entre esses escores de 0,48; 0,41;
0,32 e 0,55 em quatro amostras (média 0,44); os outros pares ficam em torno de
zero. O gerador procura, por bissecção, o ρ entre os θ que reproduz 0,44 entre
os escores (resultado: ρ(θ) ≈ 0,66 — maior porque o erro de medida dilui a
correlação observada). Consequência útil: respostas de uma dimensão dão pistas
sobre a outra, o que o classificador da abordagem 3 pode aproveitar e o TAC
por dimensão não.

## D10 — Validação externa da calibração
Os alfas de Cronbach NÃO foram usados como alvo. Mesmo assim, a base gerada
reproduz os alfas de Litzinger et al. (0,60 / 0,77 / 0,74 / 0,56):
0,608 / 0,767 / 0,740 / 0,561. Isso mostra que o gerador reproduz a estrutura
de confiabilidade do instrumento real.

## D11 — Métricas e regra de escolha comuns às três abordagens
`ils_adaptativo/metricas.py` calcula as mesmas métricas para árvore, TAC e
RL: acurácia e Kappa por dimensão, nº médio de questões (contando itens
DISTINTOS), concordância de polo+faixa e acurácia separada por faixa de
intensidade. Hiperparâmetros (ex.: profundidade) são escolhidos só na
validação; o teste é usado uma única vez, no modelo escolhido.

## D12 — Referência sem IA: "parada garantida"
6 respostas iguais em 11 já decidem o polo. Perguntar em ordem fixa (mais
discriminativo primeiro, medido no treino) e parar quando o polo estiver
decidido acerta 100% com ~32,7 questões em média (teste). É a régua real das
abordagens com IA: aceitar 10% de erro só compensa se economizar CLARAMENTE
mais questões do que essa regra.

## D13 — Árvore de decisão (linha de base): resultados e leitura
- Critério entropia (ganho de informação, mesma ideia do C4.5); uma árvore por
  dimensão; nº de questões = profundidade da folha alcançada.
- `min_amostras_folha` = 5: com 20, a árvore completa não passava de ~95%,
  porque o gabarito é função exata das 11 respostas e folhas grandes impedem
  de representá-la. Com 5, a árvore completa chega a ~100%.
- Curva em "escada": profundidades 2k e 2k−1 dão a mesma acurácia. Motivo: a
  folha prevê o lado da maioria das respostas vistas; com nº PAR de respostas,
  o empate não acrescenta informação em relação à pergunta anterior.
- Variante "todos" (pode perguntar itens de outras dimensões) deu praticamente
  o mesmo resultado: a árvore gulosa sempre acha mais informativo um item da
  própria dimensão, então não aproveita a correlação sen_int × seq_glo.
- Teste: 28,7 questões em média, acurácia 0,928 / 0,898 / 0,915 / 0,922.
  sensorial/intuitivo ficou em 0,898 (passou de 0,90 na validação):
  profundidade escolhida exatamente no limite da meta.
- TODOS os erros estão na faixa leve; nas faixas moderada e forte a acurácia é
  ~100%. Os alunos classificados errado são os que o próprio ILS considera
  "equilibrados" entre os polos.

## D14 — TAC clássico com TRI: implementação e resultados
- Calibração: 2PL estimado com girth (`twopl_mml`), uma dimensão por vez, só
  com o treino. O TAC não usa os parâmetros do gerador. Diagnóstico: a
  correlação entre o a estimado e o a do gerador foi 0,999.
- Estado do aluno: posterior de θ numa grade de 61 pontos (−4 a 4), prior
  N(0,1), estimativa EAP. Seleção: máxima informação de Fisher no θ estimado.
- catsim: usado para VALIDAR a seleção (teste automático confere que a escolha
  é idêntica à do `MaxInfoSelector` do catsim). A simulação é própria, em
  numpy vetorizado, porque (1) a regra de parada sobre o polo do ILS não existe
  no catsim e (2) simular todos os alunos juntos permite obter a curva inteira
  de limiares numa única passada.
- Alvo da parada — a decisão mais importante desta etapa:
  * "escore": P(polo do ILS completo | respostas) = respostas já dadas +
    distribuição prevista das que faltam (Poisson-binomial integrada no
    posterior de θ). É o alvo do trabalho. Quando o polo já está decidido, a
    probabilidade é 1, então o TAC nunca precisa de mais itens que a parada
    garantida.
  * "theta": P(θ > 0). Satura em ~93% de acurácia, por mais itens que faça,
    porque o sinal de θ e o polo do ILS não coincidem para alunos perto do
    meio. Mostra por que o alvo precisa ser o resultado do questionário.
- Resultados no teste (alvo "escore"):
  * limiar escolhido na validação (0,86 / 0,84 / 0,84 / 0,88): acurácia
    0,901 / 0,922 / 0,921 / 0,924 com 14,8 questões em média (todas ≥ 90%);
  * regra do projeto (95%): acurácia 0,98 em todas, com 24,2 questões.
- Comparação: TAC 14,8 × árvore 28,7 × parada garantida 32,7 questões. A
  árvore perde porque só para cedo quando a folha é pura; o TAC para quando
  ESTE aluno já está suficientemente decidido.
- Observação: o limiar de 95% é conservador (acerta ~98%); para acertar ~90%
  bastam limiares de 0,84–0,88, porque a acurácia média é maior que a
  confiança mínima exigida de cada aluno.

## D15 — Classificador MLP de respostas parciais (abordagem 3, peça a)
- Entrada com 88 valores: 44 "foi perguntado?" + 44 respostas (+1 = a,
  −1 = b, 0 = não perguntado). Saída: 4 logits, um por dimensão (um modelo só,
  para poder usar uma dimensão na previsão de outra).
- Treino com máscaras sorteadas de novo a cada época: por dimensão, nº de
  itens respondidos uniforme de 0 a 11, itens escolhidos ao acaso. Cobre os
  estados que a política de RL vai produzir (dimensões em ritmos diferentes).
- MLP 88 → 256 → 256 → 4 (ReLU), Adam (lr 0,001), BCE, lotes de 512, parada
  antecipada pela perda na validação (máscaras fixas), paciência 6.
- Referência: a probabilidade da TRI (`TAC.prob_polo_mascara`) com as mesmas
  respostas. Como a TRI conhece a "forma" do gerador, ela é praticamente o
  melhor possível usando só a própria dimensão. Se o MLP empata com ela, ele
  aprendeu o essencial sem receber a TRI pronta.
- Avaliação desta peça só na validação; o teste fica para o sistema completo.
- Prévia (MLP equivalente do scikit-learn, usada só para conferir o código
  antes de rodar o PyTorch): MLP ≈ TRI em acurácia e calibração (ECE < 0,015).
  Conhecer as outras dimensões ajuda MUITO sensorial/intuitivo e
  sequencial/global quando quase nada da própria dimensão foi respondido
  (+15 pontos com 0 itens), mas o ganho some a partir de ~4 itens próprios.
  Números oficiais (PyTorch, validação, máscaras aleatórias): acurácia MLP ×
  TRI = 0,813 × 0,815 / 0,856 × 0,845 / 0,840 × 0,840 / 0,815 × 0,802;
  ECE do MLP entre 0,008 e 0,012. Ganho por conhecer as outras dimensões com
  0 itens próprios: +0,157 (sen_int) e +0,159 (seq_glo); com 3 itens: +0,003
  e +0,011. Parada antecipada na época 54.

## D16 — Política de seleção com MaskablePPO (abordagem 3, peça b)
- Lógica do questionário em numpy puro (`ambiente.py`, testável sem PyTorch e
  capaz de jogar com milhares de alunos de uma vez para avaliar); o ambiente do
  Gymnasium (`ambiente_gym.py`) é uma casca com 1 aluno por episódio.
- Observação (92): os 88 valores do classificador + a confiança atual dele nas
  4 dimensões (2p − 1). A política não precisa reaprender o que o
  classificador já sabe; ela aprende O QUE perguntar e QUANDO parar.
- Ações (45): 44 itens + encerrar; itens já feitos são mascarados. Encerrar é
  sempre permitido; com os 44 feitos o episódio termina sozinho.
- Recompensa: −λ por pergunta; ao encerrar, +1 por dimensão em que o
  classificador acerta o polo. γ = 1, então retorno = acertos − λ·perguntas
  (λ = custo de uma pergunta medido em acertos).
- O classificador roda dentro do ambiente em numpy, com os mesmos pesos do
  PyTorch (teste automático confere a igualdade).
- Um modelo por λ (0,01; 0,02; 0,03; 0,05). Escolha do λ só na validação: o
  de menos questões entre os que deixam TODAS as dimensões ≥ 90%. O teste
  avalia apenas o escolhido.
- Avaliação determinística (ação mais provável) em lote.
- Limitação: o classificador só prevê o polo; a métrica secundária de
  intensidade fica sem valor para o RL (possível extensão: saída de faixa).

## D17 — 1ª execução do RL falhou em aprender; diagnóstico e correção
- 1ª execução (recompensa "acerto", λ 0,01/0,02/0,03/0,05; 1,5 milhão de
  passos cada), validação, pior dimensão × questões:
  0,989 × 42,9 | 0,821 × 22,0 | 0,777 × 11,5 | 0,708 × 3,8.
  O λ "escolhido" (0,01) pergunta quase tudo — pior que a parada garantida.
  Com 22 questões o RL acertou 82% onde o TAC passa de 95%: a política
  aprendida está longe do que o ambiente permite.
- Diagnóstico: uma política GULOSA escrita à mão (sem RL), no MESMO ambiente e
  com um classificador equivalente, chegou a ~14,5 questões com pior dimensão
  ≈ 0,90 (igual ao TAC). Logo o ambiente e o classificador estão bons; o
  problema é o aprendizado do PPO. Causa provável: recompensa só no fim
  (0/1 por dimensão) com 45 ações — o PPO não consegue atribuir o mérito a
  cada pergunta (problema de atribuição de crédito).
- Correção: modelagem de recompensa baseada em potencial (Ng, Harada e
  Russell, 1999): a cada pergunta, Φ(depois) − Φ(antes) − λ, com
  Φ = Σ P(polo correto). O retorno total é Φ(final) − Φ(início) − λ·n, ou
  seja, o mesmo objetivo, com sinal imediato. Teste automático confere a soma.
- Também: grade de λ mais fina (0,01 a 0,04) na região da meta e ent_coef
  0,005.
- Nova linha de base obrigatória: a política gulosa (`politica_gulosa.py`) é
  avaliada no mesmo script. Ela separa a contribuição do CLASSIFICADOR da
  contribuição do RL. Se o RL não superar a gulosa, isso deve ser dito no
  texto: o ganho viria da modelagem (classificador), não do RL.
- A 1ª execução fica registrada (experimento 2026-10-27_075247_rl) como
  resultado negativo, útil para o capítulo de Resultados.

## D18 — 2ª execução do RL (recompensa por potencial): ainda pior que as linhas de base
- λ escolhido na validação: 0,025. TESTE: 35,12 questões em média, pior
  dimensão 0,937. Cumpre a meta de 90%, mas com mais perguntas que a parada
  garantida (32,7, com 100% de acerto) e mais que o dobro do TAC (14,8).
- Política gulosa (mesmo ambiente e classificador, sem RL), TESTE: 14,37
  questões, pior dimensão 0,8995 (no limite da meta; o limiar foi escolhido na
  validação).
- Leitura: a modelagem por potencial melhorou o sinal, mas o PPO continua sem
  encontrar a política que o ambiente permite. O que funciona é a MODELAGEM
  (classificador / TRI) com uma regra de seleção simples. Resultado negativo
  do RL a relatar, não a esconder. Possível continuação (não feita): iniciar o
  PPO imitando a política gulosa (behavior cloning) e só então ajustar.

## D19 — Modelo usado na plataforma: TAC com alvo "escore"
- Escolhido o TAC (D14) com os limiares escolhidos na validação: é o único que
  cumpre a meta em TODAS as dimensões no teste (pior 0,901) com poucas
  questões (14,8). A gulosa faz 14,37, mas fica em 0,8995 numa dimensão e
  depende do PyTorch no servidor.
- Exportação: `ia/scripts/exportar_modelo.py` grava a, b (girth, treino) e os
  limiares em `plataforma/backend/app/ils/modelo_tac.json`, com o nome do
  experimento e o desempenho no teste (rastreabilidade).
- O backend tem uma cópia enxuta do TAC só com numpy (`app/ils/motor.py`); o
  teste `ia/testes/test_motor_plataforma.py` garante que ela escolhe os mesmos
  itens, para no mesmo momento e dá a mesma probabilidade que o TAC avaliado.
- Na plataforma as 4 dimensões são intercaladas (rodízio pela que tem menos
  respostas). Como no TAC as dimensões são independentes, a ordem não muda o
  resultado de nenhuma delas: o desempenho medido no teste vale para o sistema.
- Ressalva honesta: os números (14,8 questões, ≥ 90%) são da base SINTÉTICA.
  Com alunos reais do 9º ano, só um estudo comparando com o ILS completo diria
  o desempenho de verdade.

## Pendências / riscos
- As correlações de item são de universitários dos EUA, com o ILS em inglês;
  o público do sistema é o 9º ano no Brasil, com versão em português.
  Declarar como limitação.
- Circularidade (modelo aprende o gerador): discutir como limitação; usar base
  real como teste externo se for encontrada.
- Respondentes de intensidade leve (|escore| ≤ 3) concentram todos os erros
  (confirmado na árvore). Como ~40% dos alunos estão nessa faixa, a meta de
  90% exige acertar ~75–80% deles.
- O TAC já é uma linha de base forte (14,8 questões). O RL precisa ser
  comparado com ELE, não com a árvore; a vantagem esperada vem de aproveitar
  a correlação sen_int × seq_glo e de decidir as 4 dimensões em conjunto.
  Pela prévia do classificador (D15), o ganho da correlação se concentra no
  início do questionário, então a vantagem do RL sobre o TAC tende a ser
  modesta. Se for, é um resultado a discutir, não um fracasso.
