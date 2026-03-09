import re
import hmac
import hashlib


def sanitize_text(text: str, max_length: int = 280) -> str:
    """Remove caracteres de controle e limita tamanho."""
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text[:max_length].strip()


def verify_monday_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Valida HMAC-SHA256 do webhook Monday.com."""
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
