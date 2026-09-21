"""Testes do núcleo do agente (agent.py).

Três camadas, na ordem da pirâmide de testes:

    1. Unitários       — funções puras, sem rede: somar(), executar_ferramenta(),
                          carregar_contexto(). Rodam em milissegundos.
    2. Contrato        — a declaração em FERRAMENTAS bate com a função Python
                          de verdade? (o erro mais comum do template, segundo
                          o próprio README: "description vaga = ferramenta
                          ignorada" — isso pega o caso ainda pior, de parâmetro
                          que nem existe).
    3. Run-level       — o loop responder() completo, mas com o cliente da
                          OpenAI trocado por um dublê. Testa a lógica do
                          agente (decide chamar ferramenta? decide parar?)
                          sem gastar chamada de API real e sem depender de
                          o modelo responder sempre igual.

Não tem teste chamando a API de verdade aqui — isso é o tests/test_smoke.py,
que só roda com OPENAI_API_KEY configurada (veja o marker `smoke`).

Rodar:  pytest -v
"""

import inspect
import json
from types import SimpleNamespace

import agent

# ==========================================================================
# Dublês (fakes) do formato de resposta da OpenAI
# ==========================================================================
#
# Usamos SimpleNamespace em vez de MagicMock de propósito: `MagicMock(name=...)`
# não faz o que parece — `name` é reservado pelo Mock para o repr interno, não
# vira atributo. SimpleNamespace não tem essa pegadinha e deixa o teste mais
# fácil de ler.


def _fake_tool_call(call_id: str, nome: str, argumentos: dict):
    funcao = SimpleNamespace(name=nome, arguments=json.dumps(argumentos))
    return SimpleNamespace(id=call_id, function=funcao)


def _fake_message(content=None, tool_calls=None):
    msg = SimpleNamespace(content=content, tool_calls=tool_calls)
    # responder() chama recado.model_dump(exclude_none=True) para anexar a
    # mensagem do assistente ao histórico — precisa existir e devolver dict.
    msg.model_dump = lambda exclude_none=True: {
        "role": "assistant",
        "content": content,
        **({"tool_calls": tool_calls} if tool_calls else {}),
    }
    return msg


def _fake_response(message):
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _fake_cliente(respostas):
    """Cliente falso cujo .chat.completions.create() devolve, em ordem, cada
    item de `respostas` (uma lista) — ou sempre o mesmo objeto, se só um item
    for passado e o teste quiser simular "nunca conclui".

    Devolve (cliente, contador) — contador.call_count diz quantas vezes
    create() foi chamado.
    """
    fila = iter(respostas) if len(respostas) > 1 else None
    contador = SimpleNamespace(call_count=0)

    def _create(*args, **kwargs):
        contador.call_count += 1
        return next(fila) if fila is not None else respostas[0]

    completions = SimpleNamespace(create=_create)
    chat = SimpleNamespace(completions=completions)
    cliente = SimpleNamespace(chat=chat)
    return cliente, contador


# ==========================================================================
# 1. Unitários — somar()
# ==========================================================================


class TestSomar:
    def test_soma_inteiros(self):
        assert agent.somar(2, 3) == {"resultado": 5}

    def test_soma_negativos(self):
        assert agent.somar(-5, 3) == {"resultado": -2}

    def test_soma_float(self):
        assert agent.somar(1.5, 2.25) == {"resultado": 3.75}

    def test_soma_com_zero(self):
        assert agent.somar(0, 0) == {"resultado": 0}


# ==========================================================================
# 1. Unitários — executar_ferramenta()
# ==========================================================================


class TestExecutarFerramenta:
    def test_ferramenta_existente(self):
        resultado = agent.executar_ferramenta("somar", {"a": 4, "b": 6})
        assert json.loads(resultado) == {"resultado": 10}

    def test_ferramenta_inexistente_nao_quebra_e_avisa_o_modelo(self):
        resultado = agent.executar_ferramenta("nao_existe", {})
        payload = json.loads(resultado)
        assert "erro" in payload
        assert "nao_existe" in payload["erro"]

    def test_argumento_faltando_vira_erro_em_json_nao_excecao(self):
        # falta o "b" -> TypeError dentro de somar(); executar_ferramenta()
        # tem que capturar isso e devolver um erro em JSON, nunca deixar
        # a exceção subir (o agente rodaria em cima disso sem crashar).
        resultado = agent.executar_ferramenta("somar", {"a": 1})
        payload = json.loads(resultado)
        assert "erro" in payload
        assert "somar" in payload["erro"]

    def test_resultado_e_sempre_string(self):
        # o modelo só lê texto — se isto um dia virar dict/list, quebra
        # silenciosamente o contrato com a API.
        resultado = agent.executar_ferramenta("somar", {"a": 1, "b": 1})
        assert isinstance(resultado, str)


# ==========================================================================
# 1. Unitários — carregar_contexto()
# ==========================================================================


class TestCarregarContexto:
    def test_concatena_agent_md_e_memory_md(self, tmp_path, monkeypatch):
        agent_md = tmp_path / "agent.md"
        memory_md = tmp_path / "memory.md"
        agent_md.write_text("Você é um agente de teste.", encoding="utf-8")
        memory_md.write_text("- fato: usuário prefere respostas curtas", encoding="utf-8")
        monkeypatch.setattr(agent, "AGENT_MD", agent_md)
        monkeypatch.setattr(agent, "MEMORY_MD", memory_md)

        contexto = agent.carregar_contexto()

        assert "Você é um agente de teste." in contexto
        assert "usuário prefere respostas curtas" in contexto

    def test_fallback_quando_agent_md_nao_existe(self, tmp_path, monkeypatch):
        monkeypatch.setattr(agent, "AGENT_MD", tmp_path / "nao-existe.md")
        monkeypatch.setattr(agent, "MEMORY_MD", tmp_path / "tambem-nao-existe.md")

        contexto = agent.carregar_contexto()

        assert "Você é um assistente." in contexto


# ==========================================================================
# 2. Contrato — a declaração em FERRAMENTAS bate com a função Python?
# ==========================================================================


class TestContratoDasFerramentas:
    """Garante que a 'metade JSON' (o que o modelo lê) e a 'metade Python'
    (o que roda de verdade) não descolaram uma da outra. Não pega description
    vaga — isso só um teste de comportamento do modelo pegaria — mas pega o
    caso objetivo: parâmetro renomeado/removido de um lado só.
    """

    def test_parametros_declarados_batem_com_a_assinatura_real(self):
        for ferramenta in agent.FERRAMENTAS:
            nome = ferramenta["function"]["name"]
            funcao = agent.EXECUTORES[nome]
            declarados = set(ferramenta["function"]["parameters"]["properties"].keys())
            reais = set(inspect.signature(funcao).parameters.keys())
            assert declarados == reais, (
                f"'{nome}': declaração espera {declarados}, "
                f"função Python espera {reais} — desalinhado"
            )

    def test_toda_ferramenta_declarada_tem_executor_registrado(self):
        for ferramenta in agent.FERRAMENTAS:
            nome = ferramenta["function"]["name"]
            assert nome in agent.EXECUTORES, (
                f"'{nome}' está em FERRAMENTAS mas não em EXECUTORES — "
                "o modelo vai pedir e o agente não vai saber executar"
            )

    def test_toda_ferramenta_tem_description_minimamente_especifica(self):
        # Não substitui teste de comportamento (ver README: description vaga
        # = modelo ignora a ferramenta), mas pega o esquecimento óbvio.
        for ferramenta in agent.FERRAMENTAS:
            descricao = ferramenta["function"].get("description", "")
            assert len(descricao.strip()) >= 10, (
                f"'{ferramenta['function']['name']}' com description "
                "vaga demais — o modelo tende a não chamar a ferramenta"
            )


# ==========================================================================
# 3. Run-level — responder(), com o cliente da OpenAI trocado por um dublê
# ==========================================================================


class TestResponderRunLevel:
    def test_resposta_direta_em_texto_nao_chama_ferramenta(self, monkeypatch):
        resposta = _fake_response(_fake_message(content="Oi! Tudo bem?"))
        cliente, create = _fake_cliente([resposta])
        monkeypatch.setattr(agent, "get_cliente", lambda: cliente)

        mensagens = [{"role": "user", "content": "oi"}]
        resultado = agent.responder(mensagens)

        assert resultado == "Oi! Tudo bem?"
        assert create.call_count == 1
        # nenhuma mensagem role="tool" deveria ter sido anexada
        assert not any(m.get("role") == "tool" for m in mensagens)

    def test_pede_ferramenta_e_usa_o_resultado_na_resposta_final(self, monkeypatch):
        chamada = _fake_tool_call("call_1", "somar", {"a": 2, "b": 3})
        primeira = _fake_response(_fake_message(tool_calls=[chamada]))
        segunda = _fake_response(_fake_message(content="2 + 3 é 5."))
        cliente, create = _fake_cliente([primeira, segunda])
        monkeypatch.setattr(agent, "get_cliente", lambda: cliente)

        mensagens = [{"role": "user", "content": "quanto é 2 + 3?"}]
        resultado = agent.responder(mensagens)

        assert resultado == "2 + 3 é 5."
        assert create.call_count == 2

        mensagens_tool = [m for m in mensagens if m.get("role") == "tool"]
        assert len(mensagens_tool) == 1
        assert mensagens_tool[0]["tool_call_id"] == "call_1"
        assert json.loads(mensagens_tool[0]["content"]) == {"resultado": 5}

    def test_ferramenta_com_argumentos_invalidos_nao_derruba_o_loop(self, monkeypatch):
        # JSON de argumentos quebrado -> agent.py cai no except json.JSONDecodeError
        # e chama a ferramenta com {} em vez de crashar.
        chamada = SimpleNamespace(
            id="call_x",
            function=SimpleNamespace(name="somar", arguments="{not valid json"),
        )
        primeira = _fake_response(_fake_message(tool_calls=[chamada]))
        segunda = _fake_response(_fake_message(content="não consegui somar"))
        cliente, create = _fake_cliente([primeira, segunda])
        monkeypatch.setattr(agent, "get_cliente", lambda: cliente)

        mensagens = [{"role": "user", "content": "soma isso aí"}]
        resultado = agent.responder(mensagens)

        assert resultado == "não consegui somar"
        mensagens_tool = [m for m in mensagens if m.get("role") == "tool"]
        payload = json.loads(mensagens_tool[0]["content"])
        # não fixamos o texto exato da exceção (varia entre versões do Python)
        # — o que importa é que virou erro em JSON, não crash.
        assert "erro" in payload
        assert "somar" in payload["erro"]

    def test_atinge_max_iteracoes_sem_travar_e_avisa_o_usuario(self, monkeypatch):
        # o modelo pede ferramenta pra sempre, nunca devolve texto puro.
        chamada = _fake_tool_call("call_loop", "somar", {"a": 1, "b": 1})
        resposta_repetida = _fake_response(_fake_message(tool_calls=[chamada]))
        cliente, create = _fake_cliente([resposta_repetida])  # sempre o mesmo objeto
        monkeypatch.setattr(agent, "get_cliente", lambda: cliente)

        mensagens = [{"role": "user", "content": "..."}]
        resultado = agent.responder(mensagens)

        assert "limite de iterações" in resultado.lower()
        assert create.call_count == agent.MAX_ITERACOES
