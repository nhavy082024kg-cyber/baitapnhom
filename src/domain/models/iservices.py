# Ports for things that need third-party libraries (hashing, JWT, HMAC, payment provider).
# Implemented in infrastructure/services/.

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional


class IPasswordHasher(ABC):
    @abstractmethod
    def hash(self, password: str) -> str: ...

    @abstractmethod
    def verify(self, password_hash: str, password: str) -> bool: ...


class ITokenService(ABC):
    @abstractmethod
    def encode(self, user_id: int, jti: str, expires_at: datetime) -> str: ...

    @abstractmethod
    def decode(self, token: str) -> dict:
        """Raises UnauthorizedException when the token is invalid or expired."""


class IDeviceSecurity(ABC):
    """Device identity + signed commands (HMAC-SHA256)."""

    @abstractmethod
    def derive_secret(self, serial_number: str) -> str: ...

    @abstractmethod
    def hash_secret(self, secret: str) -> str: ...

    @abstractmethod
    def verify_secret(self, secret: str, stored_hash: str) -> bool: ...

    @abstractmethod
    def sign_command(self, secret: str, command_id: str, serial_number: str, slot_number: int,
                     command_type: str, expires_at_iso: str) -> str: ...


class IPaymentProvider(ABC):
    name: str

    @abstractmethod
    def build_qr(self, payment_reference: str, amount, currency: str) -> str: ...

    @abstractmethod
    def verify_signature(self, raw_body: bytes, signature: Optional[str]) -> bool: ...

    @abstractmethod
    def sign(self, raw_body: bytes) -> str:
        """Only used by the mock provider (dev endpoint / tests) to fake a signed webhook."""
