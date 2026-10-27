"""Testes da etapa 4b — ambiente do questionário (numpy) e integração com Gymnasium/SB3."""

import numpy as np
import pytest

from ils_adaptativo.ambiente import (ACAO_ENCERRAR, N_ACOES, N_OBSERVACAO, ClassificadorNumpy,
                                     QuestionarioLote, jogar_lote)
from ils_adaptativo.calibracao import calibrar
from ils_adaptativo.constantes import COLUNAS_ITENS, N_ITENS
from ils_adaptativo.escore import escores, polos
from ils_adaptativo.gerador import gerar_respondentes
from ils_adaptativo.mascaras import N_ENTRADAS


def _dados(n=50, seed=0):
    rng = [np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(3)]
    par = calibrar(np.full(N_ITENS, 0.4), np.full(N_ITENS, 0.5), "item_resto", rng[0],
                   n_amostra=2000, max_iteracoes=5)
    X = gerar_respondentes(n, par.a, par.b, np.eye(4), rng[1], rng[2])[COLUNAS_ITENS].to_numpy()
    return X, polos(escores(X))


def _clf_soma():
    """Classificador "perfeito com tudo respondido": logit = soma das respostas da dimensão.

    Pesos montados à mão (sem treino): com as 44 respostas, acerta 100%.
    """
    from ils_adaptativo.constantes import itens_da_dimensao
    W = np.zeros((4, N_ENTRADAS), np.float32)
    for d in range(4):
        for i in itens_da_dimensao(d):
            W[d, N_ITENS + i - 1] = 5.0
    return ClassificadorNumpy([(W, np.zeros(4, np.float32))])


def test_observacao_e_mascara():
    X, p = _dados()
    jogo = QuestionarioLote(X, p, _clf_soma(), lam=0.1)
    obs, m = jogo.observacao(), jogo.mascara_acoes()
    assert obs.shape == (50, N_OBSERVACAO) and obs.dtype == np.float32
    assert obs.min() >= -1 and obs.max() <= 1
    assert m.shape == (50, N_ACOES) and m.all()


def test_recompensas():
    X, p = _dados()
    jogo = QuestionarioLote(X, p, _clf_soma(), lam=0.1)
    r, fim = jogo.passo(np.zeros(50, dtype=int))           # todos perguntam o item 1
    assert np.allclose(r, -0.1) and not fim.any()
    assert not jogo.mascara_acoes()[:, 0].any()             # item 1 agora proibido
    with pytest.raises(ValueError):
        jogo.passo(np.zeros(50, dtype=int))                 # perguntar de novo é inválido
    r, fim = jogo.passo(np.full(50, ACAO_ENCERRAR))
    assert fim.all() and (r >= 0).all() and (r <= 4).all()


def test_perguntar_tudo_acerta_tudo_e_encerra_sozinho():
    X, p = _dados()
    ordem = iter(range(N_ITENS))
    r = jogar_lote(X, p, _clf_soma(), lambda obs, m: np.full(len(obs), next(ordem)))
    assert (r["n_total"] == 44).all() and (r["n_questoes"] == 11).all()
    assert (r["polo"] == p).all()


def test_politica_que_encerra_logo():
    X, p = _dados()
    r = jogar_lote(X, p, _clf_soma(), lambda obs, m: np.full(len(obs), ACAO_ENCERRAR))
    assert (r["n_total"] == 0).all()


def test_classificador_numpy_igual_ao_torch():
    torch = pytest.importorskip("torch")  # noqa: F841
    from ils_adaptativo import classificador as clf
    from ils_adaptativo.mascaras import codificar, sortear_mascaras
    X, _ = _dados(200)
    modelo = clf.ClassificadorParcial((32, 16))
    m = sortear_mascaras(len(X), np.random.default_rng(0))
    p_torch = clf.prever_proba(modelo, X, m)
    p_np = ClassificadorNumpy.de_torch(modelo).prob(codificar(X, m))
    assert np.allclose(p_torch, p_np, atol=1e-5)


def test_ambiente_gymnasium():
    pytest.importorskip("gymnasium")
    from ils_adaptativo.ambiente_gym import AmbienteILS
    X, p = _dados()
    env = AmbienteILS(X, p, _clf_soma(), lam=0.05)
    obs, _ = env.reset(seed=0)
    assert env.observation_space.contains(obs)
    assert env.action_masks().all()
    obs, r, term, trunc, _ = env.step(3)
    assert r == pytest.approx(-0.05) and not term and not trunc
    assert not env.action_masks()[3]
    _, r, term, _, info = env.step(ACAO_ENCERRAR)
    assert term and info["n_questoes"] == 1 and 0 <= info["acertos"] <= 4


def test_maskableppo_treina_e_respeita_a_mascara():
    pytest.importorskip("sb3_contrib")
    from sb3_contrib import MaskablePPO
    from stable_baselines3.common.vec_env import DummyVecEnv, VecMonitor

    from ils_adaptativo.ambiente_gym import AmbienteILS
    X, p = _dados(200)
    clf_np = _clf_soma()
    venv = VecMonitor(DummyVecEnv([lambda: AmbienteILS(X, p, clf_np, 0.05) for _ in range(2)]))
    modelo = MaskablePPO("MlpPolicy", venv, n_steps=128, batch_size=64, n_epochs=2, gamma=1.0, seed=0,
                         device="cpu", policy_kwargs={"net_arch": [32]})
    modelo.learn(total_timesteps=512)
    # a avaliação em lote nunca pode escolher item proibido (jogar_lote levantaria erro)
    def politica(obs, m):
        return np.asarray(modelo.predict(obs, action_masks=m, deterministic=True)[0])
    r = jogar_lote(X, p, clf_np, politica)
    assert (r["n_total"] <= 44).all()


def test_recompensa_potencial_soma_o_objetivo_final():
    # Soma das recompensas "potencial" = Φ(final) − Φ(início) − λ·perguntas
    X, p = _dados()
    clf = _clf_soma()
    jogo = QuestionarioLote(X, p, clf, lam=0.05, recompensa="potencial")
    phi_inicio = jogo._potencial(np.arange(len(X)))
    total = np.zeros(len(X))
    for item in range(5):
        r, _ = jogo.passo(np.full(len(X), item))
        total += r
    r, fim = jogo.passo(np.full(len(X), ACAO_ENCERRAR))
    total += r
    assert fim.all() and np.allclose(r, 0)
    assert np.allclose(total, jogo._potencial(np.arange(len(X))) - phi_inicio - 0.05 * 5)


def test_politica_gulosa():
    from ils_adaptativo import politica_gulosa
    X, p = _dados(300)
    clf = _clf_soma()
    sempre_para = jogar_lote(X, p, clf, politica_gulosa.criar(X, 0.0))
    assert (sempre_para["n_total"] == 0).all()
    # limiar inalcançável (> 1): pergunta tudo, sem repetir item, e então acerta tudo
    r = jogar_lote(X, p, clf, politica_gulosa.criar(X, 1.01))
    assert (r["n_total"] == 44).all() and (r["polo"] == p).all()
