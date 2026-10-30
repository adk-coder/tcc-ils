# Decisões de projeto — plataforma

## P1 — Backend separado da IA
`plataforma/backend` tem ambiente Python próprio. A API não depende de PyTorch:
os modelos do questionário serão exportados para formatos leves (pesos em numpy /
árvores / parâmetros 2PL) na etapa de integração.

## P2 — Estrutura do FastAPI
`modelos.py` (tabelas SQLModel), `esquemas.py` (entrada/saída da API, separados das
tabelas para nunca expor `senha_hash`), `seguranca.py` (senhas e JWT), `deps.py`
(quem está logado e com qual perfil), `rotas/` (um arquivo por assunto).

## P3 — Autenticação
- Senha: PBKDF2-HMAC-SHA256 (biblioteca padrão), sal aleatório de 16 bytes,
  600.000 iterações, comparação em tempo constante.
- Token JWT HS256 (PyJWT) com id, perfil e validade de 60 min; segredo em variável
  de ambiente, obrigatório em produção.
- Login com a mesma mensagem para e-mail inexistente e senha errada (não revela
  quem tem conta).
- Perfis professor e aluno verificados no servidor em cada rota (`exigir_professor`,
  `exigir_aluno`), nunca só no frontend.

## P4 — LGPD (requisito não funcional)
- Minimização: só nome, e-mail e senha cifrada; nada de CPF, nascimento, telefone.
- Consentimento explícito no cadastro (`aceite_termos`), com data registrada.
- Direitos do titular (art. 18): exportar os próprios dados (`GET /auth/eu/dados`) e
  excluir a conta (`DELETE /auth/eu`), que apaga também os vínculos.
- Aluno não vê a lista de colegas da sala; só o professor dono vê.
- Sala invisível (404) para quem não é dono nem matriculado.
- Pendência: o público (9º ano) é de adolescentes; conferir com o orientador o que a
  LGPD (art. 14) exige quanto a consentimento dos responsáveis e registrar no texto.

## P5 — Banco de dados
SQLModel com `create_all` (sem ferramenta de migração, suficiente para o escopo do
TCC). Desenvolvimento e testes em SQLite; produção em PostgreSQL pela variável
`DATABASE_URL`. Testes automáticos usam SQLite em memória, um banco novo por teste.

## P6 — Módulos e exercícios
- Módulo pertence a uma sala: texto de estudo + lista de exercícios. O professor
  monta o conteúdo da própria turma (reaproveitar módulos entre salas fica para
  trabalhos futuros).
- Exercícios de múltipla escolha (2 a 5 alternativas): correção automática e
  imediata, sem ambiguidade de formato numérico.
- O aluno nunca recebe a alternativa correta antes de responder; depois de
  responder recebe correção + explicação (feedback imediato).

## P7 — Gamificação (regras em `app/gamificacao.py`, funções puras e testadas)
- Pontos: só se a PRIMEIRA tentativa no exercício estiver certa. Como a resposta
  é revelada após a 1ª tentativa, pontuar tentativas seguintes premiaria errar de
  propósito. Refazer é permitido (aprendizagem), mas não pontua.
- Streak: dias seguidos com pelo menos uma resposta, no fuso de Brasília; a
  sequência continua viva se a última atividade foi hoje ou ontem.
- Ranking por sala: soma dos pontos nos módulos da sala; empate em ordem alfabética.
  Alunos veem os colegas como "Ana S." (minimização, LGPD); o professor vê o nome
  completo. Todos os matriculados aparecem, inclusive com 0 pontos.
- Exclusão de conta apaga também as respostas; a exportação de dados as inclui.

## P8 — Frontend: Nuxt 4, SPA, design "caderno"
- Nuxt 4 em vez do Nuxt 3 do projeto: o Nuxt 3 chegou ao fim do suporte em
  31/07/2026. Estrutura com o código em `app/`.
- `ssr: false` (SPA): tudo fica atrás de login, sem necessidade de SEO; simplifica a
  autenticação e o PWA.
- Token JWT em cookie (`SameSite=Lax`, 60 min, mesma validade da API) + estado
  compartilhado; resposta 401 da API encerra a sessão.
- Organização inspirada em plataformas escolares (ex.: Plurall): início com "o que
  fazer agora", salas → módulos → exercícios, desempenho. Identidade visual própria.
- Identidade "caderno de matemática": papel quadriculado, tinta azul-escura, caneta
  azul para ações, marca-texto amarelo para pontos e destaques. Fontes Lexend (texto,
  feita para facilitar a leitura) e Bricolage Grotesque (títulos e números).
- Fontes servidas pelo próprio app (@nuxt/fonts): o navegador do aluno não consulta
  servidores do Google (minimização de dados).
- Acessibilidade: foco visível, rótulos em todos os campos, avisos com role="alert",
  respeito a "reduzir movimento".

## P9 — Frontend etapa 2: módulos, exercícios e ranking
- Correção na hora (feedback imediato): o aluno escolhe, clica em "Responder" e a
  tela mostra certo/errado, a alternativa correta e a explicação do professor.
  O "Responder" separado evita enviar por toque acidental no celular.
- Linguagem visual do caderno aplicada à correção: a alternativa escolhida ganha um
  círculo "à caneta" (traço SVG que se desenha); a certa recebe marca-texto; a
  escolhida errada fica riscada em vermelho. A cor nunca é o único sinal (há ícone
  de "certo", risco e texto), pensando em daltonismo e leitores de tela.
- Pontos aparecem só quando a API os concede (1ª tentativa certa, P7); ao refazer,
  a tela avisa que não vale pontos.
- O texto do módulo é texto simples (parágrafos separados por linha em branco), sem
  Markdown nem fórmulas por enquanto. Possível evolução: KaTeX para frações e potências.
- Ações destrutivas (apagar módulo/exercício, remover aluno, sair da sala) pedem um
  segundo clique, sem a janela de confirmação do navegador.
- Ranking ao lado dos módulos em telas grandes e abaixo deles no celular; o aluno se
  vê destacado com marca-texto e "(você)".

## P10 — Questionário de estilos de aprendizagem na plataforma (etapa 3)
- Só alunos respondem; só o próprio aluno vê o resultado (o professor não tem
  rota para isso nesta versão). Respostas e resultado entram na exportação de
  dados e são apagados com a conta. Refazer apaga o anterior (um por aluno).
- O servidor escolhe cada pergunta (`app/ils/motor.py`, ver D19) e só aceita a
  resposta da pergunta atual: evita resposta duplicada por clique duplo e
  impede que o cliente manipule a ordem. Respostas ficam salvas a cada passo,
  então o aluno pode parar e continuar depois.
- Textos dos 44 itens em `app/ils/itens.json`, separados do código. O
  repositório traz textos PROVISÓRIOS (status "PROVISORIO"); a tela avisa
  enquanto não forem trocados pela versão em português adotada no TCC. Os
  textos não foram escritos por nós de propósito: precisa ser o instrumento
  publicado, para o resultado ser comparável ao ILS. O ILS é gratuito para uso
  não comercial; tradução e uso dentro de software devem ser confirmados com
  o orientador / nos termos do autor.
- Resultado mostrado como preferência (polo em marca-texto + o polo oposto),
  com descrição curta, dica de estudo e a "certeza da IA" (probabilidade de o
  ILS completo dar o mesmo polo). Não mostramos intensidade (leve/moderada/
  forte), porque o TAC foi escolhido e avaliado pelo POLO.
- A tela lembra que estilo é preferência, não limite. Ponto para a banca: a
  literatura critica a ideia de que ensinar "no estilo" do aluno melhora o
  aprendizado; aqui o resultado serve para autoconhecimento e dicas de estudo,
  não para restringir o conteúdo que cada aluno recebe.
- Sem resposta certa ou errada, não há botão "Responder": tocar na
  alternativa envia (depois do círculo de caneta se desenhar).

### P10.1 — Textos do ILS: tradução de Lopes (2002)
- Versão em português: Anexo II de LOPES, W. M. G. *ILS – Inventário de Estilos
  de Aprendizagem de Felder-Saloman: investigação de sua validade em estudantes
  universitários de Belo Horizonte*. Dissertação (Mestrado), UFSC, 2002. É a
  tradução brasileira mais citada e tem os 44 itens na ordem original.
- Conferência: os 44 itens do `itens.json` foram comparados com o texto do
  Anexo II (enunciado, alternativas e ordem). Também foi conferido que, em todos
  os itens, a alternativa (a) corresponde ao primeiro polo da dimensão (ativo,
  sensorial, visual, sequencial), condição para o escore e para a calibração
  da IA, que é feita por número de item.
- Atualização ortográfica (Acordo de 1990), apenas acentuação e trema
  (ideia, frequentemente, sequenciais, consequências), porque o público é do
  9º ano. Nenhuma palavra foi trocada.
- Limitação: no próprio estudo de Lopes (2002), com universitários, a análise
  fatorial encontrou cargas satisfatórias em 28 dos 44 itens, e só a dimensão
  visual/verbal ficou bem formada; a autora recomenda revisão semântica. Somada
  à calibração com estatísticas de universitários dos EUA (Litzinger et al.,
  2005) e ao público do 9º ano, isso é declarado como limitação do trabalho.
- O PDF da fonte fica fora do repositório (`docs/fontes/` no `.gitignore`).

### P10.2 — Tela de resultado pensada para o aluno
- Teste com a tela anterior: mostrar os dois polos de cada par e a "certeza da IA"
  em porcentagem deixava o aluno sem saber qual era, afinal, o perfil dele.
- Nova ordem: (1) o PERFIL em uma frase ("Você aprende melhor colocando a mão na
  massa, com exemplos concretos, vendo desenhos e esquemas e seguindo um passo de
  cada vez"), com os 4 estilos em destaque; (2) "Como estudar no MatIF": as 4
  dicas juntas; (3) cada parte explicada só com o estilo do aluno (o oposto
  aparece como lembrete de que todo mundo usa os dois); (4) os números da IA
  (perguntas e "segurança" por parte) num bloco recolhido, "Como a IA chegou
  nesse resultado?", para transparência sem confundir.

## P11 — PWA (instalável no celular e no computador)
- Módulo `@vite-pwa/nuxt` (Workbox): manifesto (nome, cores do caderno, ícones)
  e service worker gerados no build. É o que torna o sistema "multiplataforma"
  com um código só: navegador, Android, iPhone e computador.
- O que fica offline: só o "casco" do app (HTML, JS, CSS, fontes, ícones). Os
  dados (exercícios, respostas, ranking, questionário) vêm sempre da API e NÃO
  são guardados no aparelho: evita mostrar dados velhos (pontos, ranking) e
  dados pessoais de um aluno num aparelho compartilhado (LGPD). Sem internet, o
  app abre e mostra um aviso.
- Atualização automática (`registerType: 'autoUpdate'`): ao publicar uma versão
  nova, o app se atualiza na próxima abertura.
- Ícones gerados de um SVG (`public/icone-app.svg`) com `@vite-pwa/assets-generator`
  (preset minimal-2023), incluindo o ícone "maskable" para Android.
- Instalação: botão na página Conta quando o navegador oferece (Chrome/Edge/
  Android); no iPhone, instrução manual (o Safari não tem convite automático).
- Requisito: PWA só funciona em HTTPS (ou localhost). No celular, só dá para
  testar depois da publicação.

## P12 — Painel do professor e "continuar de onde parou"
- Painel (`/salas/{id}/desempenho`, só o professor dono): acerto de PRIMEIRA
  tentativa por exercício (a 1ª resposta mede o que o aluno sabia antes de ver a
  correção; mesma regra dos pontos), a alternativa errada mais marcada (mostra
  QUAL confusão a turma faz, ex.: somar numeradores e denominadores), quantos
  concluíram cada módulo e, por aluno, certos, pontos e última atividade (em
  vermelho quem está há 7+ dias sem responder). "O que vale a pena revisar" lista
  os 5 exercícios com menor acerto de primeira.
- Só alunos ainda matriculados entram nas contas; os dados não saem da sala do
  professor (404 para os outros), coerente com a LGPD.
- O painel não mostra o estilo de aprendizagem dos alunos (decisão P10: o
  resultado é só do aluno).
- "Continuar de onde parou" (`/eu/continuar`): o módulo da última resposta, se
  ainda faltar exercício; senão o próximo da mesma sala; senão qualquer módulo
  com exercício pendente. Sem pendências, o início diz que o aluno está em dia.

## P14 — Adesivos de conquista (gamificação)
- 8 adesivos, como figurinhas coladas no caderno (mesma identidade visual):
  primeiro acerto, 5 acertos de primeira, 10 exercícios diferentes, acertar um
  exercício que tinha errado ("Não desisto"), concluir um módulo, 3 e 7 dias
  seguidos, e descobrir o estilo de aprendizagem.
- Por quê: pontos e ranking já existiam, mas o ranking COMPARA alunos e pode
  desmotivar quem fica nas últimas posições. Os adesivos premiam o progresso de
  cada aluno contra si mesmo, inclusive a persistência (errar e tentar de novo),
  e não só o desempenho.
- Calculados na hora a partir das respostas (função pura `app/conquistas.py`,
  testada), sem tabela nova: nenhum dado pessoal novo é guardado (LGPD), e uma
  mudança de regra vale também para conquistas antigas.
- Aviso "Novo adesivo!" ao ganhar (depois de responder um exercício ou concluir
  o questionário). Os adesivos são só do aluno: não aparecem para colegas nem
  para o professor.

## P13 — Publicação (Neon + Render, planos gratuitos)
- Banco: PostgreSQL no Neon, região São Paulo (dados no Brasil; plano gratuito
  permanente, 1 GB). API e site: Render (plano gratuito), descritos em
  `render.yaml` na raiz (infraestrutura como código: o ambiente é reproduzível).
- Segredos (endereço do banco, chave do JWT) ficam só no painel do Render; a
  chave do JWT é gerada pelo próprio Render. `AMBIENTE=producao` faz a API se
  recusar a subir sem um segredo próprio.
- HTTPS fornecido pelo Render: requisito do PWA e da LGPD (dados em trânsito
  cifrados). CORS liberado só para o endereço do site.
- Limitação do plano gratuito: a API "dorme" após ~15 min sem uso e o primeiro
  acesso depois disso demora (~1 min); o Neon também suspende o banco parado
  (tratado com `pool_pre_ping`). Aceitável para um protótipo de TCC; em uso real
  numa escola, seria preciso um plano pago ou um servidor da instituição.
- A API fica nos EUA (o Render não tem região no Brasil) e o banco em São Paulo:
  os dados ficam armazenados no Brasil, mas trafegam pela API nos EUA. Ponto a
  citar na discussão de LGPD (transferência internacional, art. 33).
