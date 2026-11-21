from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.common.models import Base, CreateAtMixin, UpdateAtMixin


class Order(Base, CreateAtMixin, UpdateAtMixin):
    """订单（判责事实来源）"""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    order_no: Mapped[str] = mapped_column(String(40), unique=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    product_name: Mapped[str] = mapped_column(String(300))
    category: Mapped[str] = mapped_column(String(30))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(30))
    merchant: Mapped[str] = mapped_column(String(200))
    logistics_no: Mapped[str | None] = mapped_column(String(60))
    logistics_status: Mapped[str | None] = mapped_column(String(50))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False)
    is_fresh: Mapped[bool] = mapped_column(Boolean, default=False)
    is_large: Mapped[bool] = mapped_column(Boolean, default=False)
    is_installed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_digital: Mapped[bool] = mapped_column(Boolean, default=False)
