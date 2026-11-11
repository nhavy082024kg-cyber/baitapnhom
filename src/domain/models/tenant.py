from datetime import datetime
from typing import Optional

from domain.models.base import entity


@entity
class Tenant:
    """A perfume brand. Every business table references it through tenant_id."""
    id: Optional[int] = None
    name: str
    code: str
    status: str = "ACTIVE"
    logo_url: Optional[str] = None
    description: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    created_at: Optional[datetime] = None
