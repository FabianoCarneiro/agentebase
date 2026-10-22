"""Testes do roteador de canary (router/router.py).

Só a decisão de destino — escolher_destino() é pura, então dá para cobrir
todos os casos sem subir servidor nem sortear de verdade: o `sorteio` é
passado na mão.

Rodar:  pytest tests/test_router.py -v
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "router"))

import router  # noqa: E402 — precisa do sys.path acima

pytestmark = pytest.mark.unitario


class TestEscolherDestino:
    def test_pct_zero_vai_sempre_para_o_estavel(self):
        assert router.escolher_destino(0, None, 0.0) == "estavel"

    def test_pct_cem_vai_sempre_para_o_canary(self):
        assert router.escolher_destino(100, None, 0.999) == "canary"

    def test_sorteio_abaixo_do_pct_vai_para_o_canary(self):
        assert router.escolher_destino(10, None, 0.05) == "canary"

    def test_sorteio_na_fronteira_vai_para_o_estavel(self):
        # 0.10 não é < 0.10: a fronteira pertence ao estável
        assert router.escolher_destino(10, None, 0.10) == "estavel"

    def test_cookie_mantem_o_visitante_no_canary(self):
        assert router.escolher_destino(10, "canary", 0.99) == "canary"

    def test_cookie_mantem_o_visitante_no_estavel(self):
        assert router.escolher_destino(50, "estavel", 0.0) == "estavel"

    def test_pct_zero_ignora_cookie_de_canary(self):
        # rollback: quem estava no canary tem que voltar para o estável
        assert router.escolher_destino(0, "canary", 0.0) == "estavel"

    def test_cookie_invalido_e_ignorado(self):
        assert router.escolher_destino(10, "lixo", 0.05) == "canary"


class TestConfig:
    def test_config_do_repositorio_e_valido(self):
        config = router.carregar_config()
        assert 0 <= config["pct"] <= 100
        assert set(config["urls"]) == set(router.DESTINOS)
