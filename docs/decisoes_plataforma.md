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

## P6 — Gamificação
- Pontos: cada exercício vale `pontos` (padrão 10), ganhos só se a PRIMEIRA tentativa
  do aluno estiver certa. Tentar de novo não rende pontos — senão bastaria errar de
  propósito, ver a resposta e acertar em seguida.
- Streak: número de dias seguidos em que o aluno respondeu pelo menos um exercício,
  contados no fuso de Brasília (`ZoneInfo("America/Sao_Paulo")`). A sequência ainda
  está viva se o último dia de atividade foi hoje ou ontem.
- Ranking: por sala, soma dos pontos dos exercícios dos módulos daquela sala; empate
  desfeito por ordem alfabética. Para os colegas, o nome aparece abreviado ("Ana L.");
  o professor vê o nome completo. O aluno não sabe o `id` dos colegas.
- Todas as regras estão em `gamificacao.py` como funções puras (fáceis de testar e
  de documentar no texto do TCC).
