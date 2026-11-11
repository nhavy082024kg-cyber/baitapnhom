import hashlib
import hmac
from datetime import datetime

import jwt
from werkzeug.security import check_password_hash, generate_password_hash

from domain.exceptions import UnauthorizedException
from domain.models.iservices import IDeviceSecurity, IPasswordHasher, ITokenService


class PasswordHasher(IPasswordHasher):
    def hash(self, password: str) -> str:
        return generate_password_hash(password)

    def verify(self, password_hash: str, password: str) -> bool:
        return check_password_hash(password_hash, password)


class TokenService(ITokenService):
    """JWT (HS256). `jti` links the token to a row in user_sessions so it can be revoked."""

    def __init__(self, secret_key: str):
        self.secret_key = secret_key

    def encode(self, user_id: int, jti: str, expires_at: datetime) -> str:
        # naive datetimes are treated as UTC by PyJWT
        return jwt.encode({"sub": str(user_id), "jti": jti, "exp": expires_at}, self.secret_key, algorithm="HS256")

    def decode(self, token: str) -> dict:
        try:
            return jwt.decode(token, self.secret_key, algorithms=["HS256"])
        except jwt.PyJWTError:
            raise UnauthorizedException("Invalid or expired token")


class DeviceSecurity(IDeviceSecurity):
    """
    Device identity:   secret = HMAC(master_key, serial)   (shown ONCE when the machine is registered)
    Server stores only sha256(secret). Commands are signed with the same secret,
    so the device can verify that a command really comes from the backend.
    """

    def __init__(self, master_key: str):
        self.master_key = master_key.encode()

    def derive_secret(self, serial_number: str) -> str:
        return hmac.new(self.master_key, f"device:{serial_number}".encode(), hashlib.sha256).hexdigest()

    def hash_secret(self, secret: str) -> str:
        return hashlib.sha256(secret.encode()).hexdigest()

    def verify_secret(self, secret: str, stored_hash: str) -> bool:
        return hmac.compare_digest(self.hash_secret(secret or ""), stored_hash or "")

    def sign_command(self, secret: str, command_id: str, serial_number: str, slot_number: int,
                     command_type: str, expires_at_iso: str) -> str:
        message = f"{command_id}|{serial_number}|{slot_number}|{command_type}|{expires_at_iso}"
        return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
