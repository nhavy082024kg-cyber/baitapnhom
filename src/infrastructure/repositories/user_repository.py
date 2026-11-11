from datetime import datetime
from typing import List, Optional, Set

from domain.exceptions import ValidationException
from domain.models.irepositories import ISessionRepository, ITenantRepository, IUserRepository
from domain.models.tenant import Tenant
from domain.models.user import User, UserSession
from infrastructure.models.tenant_model import TenantModel
from infrastructure.models.user_models import (PermissionModel, RoleModel, RolePermissionModel, UserModel,
                                               UserRoleModel, UserSessionModel)
from infrastructure.repositories.base_repository import SqlRepository


class TenantRepository(SqlRepository, ITenantRepository):
    model, entity = TenantModel, Tenant

    def add(self, tenant): return self._add(tenant)
    def get(self, tenant_id): return self._first(id=tenant_id)
    def get_by_code(self, code): return self._first(code=code)
    def list(self): return self._all()
    def update(self, tenant): return self._save(tenant)


class UserRepository(SqlRepository, IUserRepository):
    model, entity = UserModel, User

    def add(self, user: User, role_codes: List[str]) -> User:
        created = self._add(user)
        for code in role_codes:
            role = self.session.query(RoleModel).filter(RoleModel.tenant_id.is_(None), RoleModel.code == code).first()
            if role is None:
                raise ValidationException(f"Unknown role: {code}")
            self.session.add(UserRoleModel(user_id=created.id, role_id=role.id))
        self.session.flush()
        return created

    def get(self, user_id): return self._first(id=user_id)
    def get_by_email(self, email): return self._first(email=email)

    def list_by_tenant(self, tenant_id: Optional[int]) -> List[User]:
        query = self.session.query(UserModel)
        if tenant_id is not None:
            query = query.filter(UserModel.tenant_id == tenant_id)
        return self._to_entities(query.order_by(UserModel.id).all())

    def update(self, user): return self._save(user)

    def get_role_codes(self, user_id: int) -> List[str]:
        rows = (self.session.query(RoleModel.code).join(UserRoleModel, UserRoleModel.role_id == RoleModel.id)
                .filter(UserRoleModel.user_id == user_id).distinct().all())
        return sorted(r[0] for r in rows)

    def get_permission_codes(self, user_id: int) -> Set[str]:
        rows = (self.session.query(PermissionModel.code)
                .join(RolePermissionModel, RolePermissionModel.permission_id == PermissionModel.id)
                .join(UserRoleModel, UserRoleModel.role_id == RolePermissionModel.role_id)
                .filter(UserRoleModel.user_id == user_id).distinct().all())
        return {r[0] for r in rows}


class SessionRepository(SqlRepository, ISessionRepository):
    model, entity = UserSessionModel, UserSession

    def add(self, session): return self._add(session)
    def get_by_jti(self, jti): return self._first(token_jti=jti)
    def update(self, session): return self._save(session)

    def revoke_all_for_user(self, user_id: int, revoked_at: datetime) -> int:
        return (self.session.query(UserSessionModel)
                .filter(UserSessionModel.user_id == user_id, UserSessionModel.revoked_at.is_(None))
                .update({"revoked_at": revoked_at}, synchronize_session=False))
