# Plataforma

- `backend/`  — FastAPI + SQLModel, autenticação JWT (professor/aluno), PostgreSQL em produção
- `frontend/` — Nuxt 3 (PWA) — próxima etapa

## Backend: como rodar (Windows, PowerShell)

```powershell
cd plataforma\backend
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest                                  # 22 testes
uvicorn app.main:app --reload           # API em http://localhost:8000
```

Abra http://localhost:8000/docs para testar as rotas pelo navegador.

O ambiente do backend é SEPARADO do ambiente da IA (`ia/.venv`), para não carregar
PyTorch na API. Configurações: copie `.env.exemplo` para `.env` (ver `app/config.py`).
Sem configurar nada, a API usa SQLite (`dev.db`); para PostgreSQL, veja `docker-compose.yml`.

## Rotas desta etapa

| Método | Rota | Quem | O que faz |
|---|---|---|---|
| POST | /auth/registrar | todos | cadastro (exige aceite dos termos) |
| POST | /auth/login | todos | devolve o token JWT |
| GET | /auth/eu | logado | dados da conta |
| GET | /auth/eu/dados | logado | exporta tudo o que o sistema guarda (LGPD) |
| DELETE | /auth/eu | logado | exclui a conta (LGPD) |
| POST | /salas | professor | cria sala com código de convite |
| GET | /salas | logado | salas do professor / do aluno |
| POST | /salas/entrar | aluno | entra numa sala pelo código |
| GET | /salas/{id} | dono ou matriculado | detalhes (lista de alunos só para o professor) |
| DELETE | /salas/{id}/alunos/{aluno_id} | professor dono | remove aluno |
| DELETE | /salas/{id}/sair | aluno | sai da sala |
| POST | /salas/{id}/modulos | professor dono | cria módulo (texto de estudo) |
| GET | /salas/{id}/modulos | dono ou matriculado | lista módulos (aluno vê quantos já acertou) |
| GET | /modulos/{id} | dono ou matriculado | módulo com exercícios (aluno NÃO recebe a resposta) |
| PUT / DELETE | /modulos/{id} | professor dono | edita / apaga (com exercícios e respostas) |
| POST | /modulos/{id}/exercicios | professor dono | cria exercício de múltipla escolha |
| PUT / DELETE | /exercicios/{id} | professor dono | edita / apaga |
| POST | /exercicios/{id}/responder | aluno matriculado | responde; recebe correção, explicação e pontos |
| GET | /eu/progresso | aluno | pontos, exercícios acertados, streak atual e melhor streak |
| GET | /salas/{id}/ranking | dono ou matriculado | ranking da sala (nomes abreviados para alunos) |
