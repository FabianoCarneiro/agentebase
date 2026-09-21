"""Smoke test com a API da OpenAI de verdade — o único teste deste projeto
que gasta chamada real e não é 100% determinístico.

Por isso ele:
  - fica isolado num arquivo separado dos testes unitários/run-level;
  - só roda se OPENAI_API_KEY estiver configurada (senão, skip — nunca falha
    o CI de quem não tem a chave);
  - tem o marker `smoke`, então o CI de todo PR roda com `pytest -m "not
    smoke"` e ignora este arquivo. Rode manualmente com:

        pytest -m smoke -v

Serve para pegar o que um mock nunca vai pegar: mudança de modelo, chave
revogada, mudança no formato da resposta da API, etc. — coisas de
integração de verdade, não de lógica do agente.
"""

import os

import pytest

import agent

pytestmark = pytest.mark.smoke

requer_chave_real = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="precisa de OPENAI_API_KEY de verdade — não roda no CI de PR por padrão",
)


@requer_chave_real
def test_agente_soma_de_verdade_via_ferramenta():
    mensagens = [
        {"role": "system", "content": agent.carregar_contexto()},
        {"role": "user", "content": "quanto é 1234 mais 5678? responda só o número"},
    ]

    resposta = agent.responder(mensagens)

    assert "6912" in resposta
