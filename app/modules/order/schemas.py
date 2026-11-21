from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_no: str
    product_name: str
    category: str
    amount: Decimal
    status: str
    merchant: str
    logistics_no: str | None = None
    logistics_status: str | None = None
    paid_at: datetime | None = None
    shipped_at: datetime | None = None
    delivered_at: datetime | None = None
    is_custom: bool = False
    is_fresh: bool = False
    is_large: bool = False
    is_installed: bool = False
    is_digital: bool = False
