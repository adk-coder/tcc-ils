"""O motor da plataforma (plataforma/backend/app/ils/motor.py) decide IGUAL ao TAC avaliado.

O backend tem uma cópia enxuta do TAC (só numpy). Este teste garante que a cópia não
diverge: para muitas sequências de respostas, as duas implementações escolhem o mesmo
próximo item, param no mesmo momento e dão a mesma probabilidade do polo.
"""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from ils_adaptativo.tac import TAC

CAMINHO = Path(__file__).resolve().parents[2] / "plataforma" / "backend" / "app" / "ils" / "motor.py"


def _carregar_motor():
    if not CAMINHO.exists():
        pytest.skip("plataforma/backend não encontrada")
    spec = importlib.util.spec_from_file_location("motor_plataforma", CAMINHO)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_motor_da_plataforma_igual_ao_tac():
    modulo = _carregar_motor()
    rng = np.random.default_rng(7)
    a, b = rng.uniform(0.4, 2.5, 44), rng.normal(0, 0.8, 44)
    limiares = [0.86, 0.84, 0.84, 0.88]

    tac = TAC()
    tac.a, tac.b = a.copy(), b.copy()
    motor = modulo.MotorILS(a, b, limiares)

    for _ in range(200):                                   # 200 alunos simulados
        d = int(rng.integers(4))
        respostas: dict[int, int] = {}
        while True:
            esperado = tac.proxima_questao(d, dict(respostas), limiares[d], alvo="escore")
            obtido = motor.avaliar_dimensao(d, dict(respostas))
            assert esperado[:2] == obtido[:2]
            assert esperado[2] == pytest.approx(obtido[2], abs=1e-12)
            if esperado[0] is None:
                break
            respostas[esperado[0]] = int(rng.random() < 0.5)
