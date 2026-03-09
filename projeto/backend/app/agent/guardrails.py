"""
Guardrails do agente: validação de tokens, limite de mensagens e detecção de off-topic.
"""

# Palavras-chave claramente fora do escopo de consultoria Monday.com
_OFF_TOPIC_KEYWORDS = [
    "piada", "receita", "culinária", "futebol", "esporte", "política",
    "religião", "sexo", "violência", "hack", "crack software",
    "download grátis", "torrent", "como fazer bomba", "droga",
]


class GuardrailsChecker:
    def __init__(self, max_input_tokens: int = 500, max_messages: int = 15):
        self.max_input_tokens = max_input_tokens
        self.max_messages = max_messages

    def estimate_tokens(self, content: str) -> int:
        """Estimativa simples: ~4 caracteres por token."""
        return max(1, len(content) // 4)

    def validate_input(self, content: str) -> tuple[bool, str | None]:
        """
        Valida conteúdo da mensagem do usuário.
        Retorna (válido, mensagem_de_erro).
        """
        if not content or not content.strip():
            return False, "Mensagem vazia"

        tokens = self.estimate_tokens(content)
        if tokens > self.max_input_tokens:
            return False, (
                f"Mensagem muito longa (~{tokens} tokens). "
                f"Limite: {self.max_input_tokens} tokens."
            )

        return True, None

    def check_message_limit(self, total_messages: int) -> tuple[str, bool]:
        """
        Verifica o limite de mensagens da sessão.

        Retorna (status, bloqueado):
        - status: 'ok' | 'penultimate' | 'final'
        - bloqueado: True se a sessão não pode mais receber mensagens
        """
        if total_messages >= self.max_messages:
            return "final", True
        if total_messages == self.max_messages - 1:
            return "penultimate", False
        return "ok", False

    def is_penultimate(self, total_messages: int) -> bool:
        """Retorna True se a próxima troca será a penúltima."""
        return total_messages == self.max_messages - 2

    def detect_off_topic(self, content: str) -> bool:
        """Heurística simples para detectar mensagens fora do escopo."""
        content_lower = content.lower()
        return any(kw in content_lower for kw in _OFF_TOPIC_KEYWORDS)
