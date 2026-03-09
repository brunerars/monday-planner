"""
Testes isolados dos guardrails e do ContextManager.
Não requerem DB ou Claude API real.
"""
import pytest

from app.agent.guardrails import GuardrailsChecker
from app.agent.prompts import (
    CONTEXT_COMPRESSION_PROMPT,
    FINAL_NOTE,
    PENULTIMATE_NOTE,
    build_plan_generation_prompt,
    build_system_prompt,
)


# ── GuardrailsChecker ─────────────────────────────────────────────────────


class TestGuardrails:
    def setup_method(self):
        self.g = GuardrailsChecker(max_input_tokens=500, max_messages=15)

    # estimate_tokens
    def test_estimate_tokens_basico(self):
        assert self.g.estimate_tokens("a" * 400) == 100

    def test_estimate_tokens_minimo(self):
        assert self.g.estimate_tokens("x") >= 1

    # validate_input
    def test_input_valido(self):
        ok, err = self.g.validate_input("Olá, tudo bem?")
        assert ok is True
        assert err is None

    def test_input_vazio(self):
        ok, err = self.g.validate_input("")
        assert ok is False
        assert err is not None

    def test_input_so_espacos(self):
        ok, err = self.g.validate_input("   ")
        assert ok is False

    def test_input_muito_longo(self):
        # 500 tokens * 4 chars = 2000 chars > limite
        long_content = "a" * 2100
        ok, err = self.g.validate_input(long_content)
        assert ok is False
        assert "longa" in err.lower() or "tokens" in err.lower()

    def test_input_no_limite_exato(self):
        # exatamente 500 tokens = 2000 chars
        content = "a" * 2000
        ok, _ = self.g.validate_input(content)
        assert ok is True

    # check_message_limit
    def test_limite_ok(self):
        status, blocked = self.g.check_message_limit(5)
        assert status == "ok"
        assert blocked is False

    def test_limite_penultimate(self):
        # 14 mensagens → penúltima troca
        status, blocked = self.g.check_message_limit(14)
        assert status == "penultimate"
        assert blocked is False

    def test_limite_final(self):
        status, blocked = self.g.check_message_limit(15)
        assert status == "final"
        assert blocked is True

    def test_limite_alem_do_maximo(self):
        status, blocked = self.g.check_message_limit(20)
        assert blocked is True

    # detect_off_topic
    def test_off_topic_detectado(self):
        assert self.g.detect_off_topic("me conta uma piada") is True

    def test_off_topic_nao_detectado(self):
        assert self.g.detect_off_topic("como funciona o funil de vendas?") is False

    def test_off_topic_seguro(self):
        assert self.g.detect_off_topic("Usamos Pipedrive como CRM hoje") is False


# ── Prompts ───────────────────────────────────────────────────────────────


class TestPrompts:
    def _make_lead(self, **kwargs):
        """Cria um objeto simples que imita o modelo Lead."""
        class FakeLead:
            tipo_negocio = "B2B"
            segmento = "Tecnologia"
            empresa = "Acme Ltda"
            porte = "ME"
            colaboradores = "11-50"
            areas_interesse = ["Vendas", "Projetos"]
            dor_principal = "Processos manuais"
            usa_monday = "avaliando"
            nome_contato = "João"

        lead = FakeLead()
        for k, v in kwargs.items():
            setattr(lead, k, v)
        return lead

    def test_system_prompt_contem_empresa(self):
        lead = self._make_lead()
        prompt = build_system_prompt(lead)
        assert "Acme Ltda" in prompt

    def test_system_prompt_contem_areas(self):
        lead = self._make_lead()
        prompt = build_system_prompt(lead)
        assert "Vendas" in prompt
        assert "Projetos" in prompt

    def test_system_prompt_campos_opcionais_ausentes(self):
        lead = self._make_lead(colaboradores=None, usa_monday=None, dor_principal=None)
        prompt = build_system_prompt(lead)
        assert "não informado" in prompt

    def test_penultimate_note_presente(self):
        assert "penúltima" in PENULTIMATE_NOTE.lower() or "última oportunidade" in PENULTIMATE_NOTE.lower()

    def test_final_note_presente(self):
        assert "Encerre" in FINAL_NOTE or "encerre" in FINAL_NOTE.lower()

    def test_plan_prompt_contem_empresa(self):
        lead = self._make_lead()
        prompt = build_plan_generation_prompt(lead, "CONSULTOR: Olá!\nCLIENTE: Oi")
        assert "Acme Ltda" in prompt
        assert "SUMMARY_JSON" in prompt

    def test_plan_prompt_contem_historico(self):
        lead = self._make_lead()
        historico = "CONSULTOR: Olá!\nCLIENTE: Tudo bem"
        prompt = build_plan_generation_prompt(lead, historico)
        assert historico in prompt

    def test_compression_prompt_tem_placeholder(self):
        filled = CONTEXT_COMPRESSION_PROMPT.format(messages="USER: Oi\nASSISTANT: Olá")
        assert "USER: Oi" in filled
        assert "{messages}" not in filled


# ── Guardrails com configuração personalizada ─────────────────────────────


class TestGuardrailsCustom:
    def test_limite_customizado(self):
        g = GuardrailsChecker(max_input_tokens=100, max_messages=5)
        # 5 mensagens deve ser final
        _, blocked = g.check_message_limit(5)
        assert blocked is True
        # 4 mensagens deve ser penultimate
        status, _ = g.check_message_limit(4)
        assert status == "penultimate"

    def test_token_limit_customizado(self):
        g = GuardrailsChecker(max_input_tokens=10, max_messages=15)
        # 11 tokens = 44 chars (44//4=11 > 10 → falha)
        ok, _ = g.validate_input("a" * 44)
        assert ok is False
        # 10 tokens = 40 chars (40//4=10, não > 10 → passa)
        ok, _ = g.validate_input("a" * 40)
        assert ok is True
