from datetime import datetime
from decimal import Decimal
from typing import Optional

from domain.models.base import entity


@entity
class Location:
    id: Optional[int] = None
    tenant_id: int
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    status: str = "ACTIVE"


@entity
class Product:
    id: Optional[int] = None
    tenant_id: int
    sku: str
    name: str
    default_price_per_spray: Decimal
    description: Optional[str] = None
    image_url: Optional[str] = None
    top_notes: Optional[str] = None
    middle_notes: Optional[str] = None
    base_notes: Optional[str] = None
    usage_instructions: Optional[str] = None
    product_qr_url: Optional[str] = None
    is_available: bool = True
    created_at: Optional[datetime] = None
