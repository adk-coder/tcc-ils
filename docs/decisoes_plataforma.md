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
