import hashlib
import hmac
from typing import Optional

from domain.models.iservices import IPaymentProvider


class MockPaymentProvider(IPaymentProvider):
    """
    Stand-in for a real QR payment provider (VietQR, MoMo, VNPay sandbox...).
    The webhook body is signed with HMAC-SHA256(webhook_secret, raw_body) and sent in header X-Signature.
    To use a real provider: write another class implementing IPaymentProvider and change dependency_container.py.
    """
    name = "MOCK"

    def __init__(self, webhook_secret: str):
        self.webhook_secret = webhook_secret.encode()

    def build_qr(self, payment_reference: str, amount, currency: str) -> str:
        return f"scentstation-pay://{payment_reference}?amount={amount}&currency={currency}"

    def sign(self, raw_body: bytes) -> str:
        return hmac.new(self.webhook_secret, raw_body, hashlib.sha256).hexdigest()

    def verify_signature(self, raw_body: bytes, signature: Optional[str]) -> bool:
        if not signature:
            return False
        return hmac.compare_digest(self.sign(raw_body), signature.strip().lower())
