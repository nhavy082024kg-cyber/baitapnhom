import uuid
from datetime import timedelta
from typing import Optional

from domain.clock import utcnow
from domain.constants import TenantStatus, UserStatus
from domain.exceptions import UnauthorizedException
from domain.models.irepositories import ISessionRepository, ITenantRepository, IUnitOfWork, IUserRepository
from domain.models.iservices import IPasswordHasher, ITokenService
from domain.models.settings import ServiceSettings
from domain.models.user import AuthContext, UserSession
from services.audit_service import AuditService


class AuthService:
    def __init__(self, users: IUserRepository, sessions: ISessionRepository, tenants: ITenantRepository,
                 hasher: IPasswordHasher, tokens: ITokenService, audit: AuditService,
                 uow: IUnitOfWork, settings: ServiceSettings, clock=utcnow):
        self.users = users
        self.sessions = sessions
        self.tenants = tenants
        self.hasher = hasher
        self.tokens = tokens
        self.audit = audit
        self.uow = uow
        self.settings = settings
        self.clock = clock

    def login(self, email: str, password: str, ip: Optional[str] = None, device_info: Optional[str] = None) -> dict:
        now = self.clock()
        user = self.users.get_by_email((email or "").strip().lower())
        if user is None:
            raise UnauthorizedException("Invalid email or password")
        if user.status != UserStatus.ACTIVE.value:
            raise UnauthorizedException("Account is locked or inactive")
        if user.tenant_id is not None:
            tenant = self.tenants.get(user.tenant_id)
            if tenant is None or tenant.status != TenantStatus.ACTIVE.value:
                raise UnauthorizedException("Brand workspace is not active")

        if not self.hasher.verify(user.password_hash, password or ""):
            user.failed_login_count += 1
            if user.failed_login_count >= self.settings.max_failed_logins:
                user.status = UserStatus.LOCKED.value
            self.users.update(user)
            self.audit.record(action="LOGIN_FAILED", target_type="user", target_id=user.id,
                              tenant_id=user.tenant_id, actor_id=user.id, severity="WARNING", source_ip=ip,
                              after={"failed_login_count": user.failed_login_count, "status": user.status})
            self.uow.commit()          # keep the failed counter even though we raise
            raise UnauthorizedException("Invalid email or password")

        user.failed_login_count = 0
        user.last_login_at = now
        self.users.update(user)

        jti = uuid.uuid4().hex
        expires_at = now + timedelta(minutes=self.settings.token_ttl_minutes)
        self.sessions.add(UserSession(user_id=user.id, token_jti=jti, expires_at=expires_at,
                                      ip_address=ip, device_info=device_info))
        token = self.tokens.encode(user.id, jti, expires_at)
        self.audit.record(action="LOGIN", target_type="user", target_id=user.id,
                          tenant_id=user.tenant_id, actor_id=user.id, source_ip=ip)
        self.uow.commit()
        return {"token": token, "expires_at": expires_at, "user": user,
                "roles": self.users.get_role_codes(user.id),
                "permissions": sorted(self.users.get_permission_codes(user.id))}

    def authenticate(self, token: str) -> AuthContext:
        """Called on every protected request: JWT valid + session not revoked + account still active."""
        now = self.clock()
        claims = self.tokens.decode(token)
        session = self.sessions.get_by_jti(claims.get("jti", ""))
        if session is None or session.revoked_at is not None or session.expires_at <= now:
            raise UnauthorizedException("Session expired or revoked")
        user = self.users.get(int(claims["sub"]))
        if user is None or user.status != UserStatus.ACTIVE.value:
            raise UnauthorizedException("Account is not active")
        return AuthContext(
            user_id=user.id, tenant_id=user.tenant_id, email=user.email,
            roles=self.users.get_role_codes(user.id),
            permissions=self.users.get_permission_codes(user.id),
            jti=session.token_jti, step_up_verified_until=session.step_up_verified_until,
        )

    def logout(self, ctx: AuthContext) -> None:
        session = self.sessions.get_by_jti(ctx.jti)
        if session and session.revoked_at is None:
            session.revoked_at = self.clock()
            self.sessions.update(session)
            self.audit.record_user(ctx, "LOGOUT", "user", target_id=ctx.user_id)
            self.uow.commit()

    def step_up(self, ctx: AuthContext, password: str) -> dict:
        """Re-enter the password to unlock sensitive actions (refund, test spray) for a few minutes."""
        user = self.users.get(ctx.user_id)
        if user is None or not self.hasher.verify(user.password_hash, password or ""):
            self.audit.record_user(ctx, "STEP_UP_FAILED", "user", target_id=ctx.user_id, severity="WARNING")
            self.uow.commit()
            raise UnauthorizedException("Invalid password")
        session = self.sessions.get_by_jti(ctx.jti)
        session.step_up_verified_until = self.clock() + timedelta(minutes=self.settings.step_up_minutes)
        self.sessions.update(session)
        self.audit.record_user(ctx, "STEP_UP", "user", target_id=ctx.user_id)
        self.uow.commit()
        return {"step_up_verified_until": session.step_up_verified_until}
