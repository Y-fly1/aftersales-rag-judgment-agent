from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.models import Base, CreateAtMixin, UpdateAtMixin


class Ticket(Base, CreateAtMixin, UpdateAtMixin):
    """售后工单：一次判责的完整留痕"""

    __tablename__ = "tickets"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[int] = mapped_column(BigInteger)
    order_no: Mapped[str] = mapped_column(String(40))
    type: Mapped[str] = mapped_column(String(30))
    reason: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="judging")
    liable_party: Mapped[str | None] = mapped_column(String(30))
    action: Mapped[str | None] = mapped_column(String(30))
    action_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    confidence: Mapped[str | None] = mapped_column(String(20))
    policy_refs: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    reasoning: Mapped[str | None] = mapped_column(Text)
    need_human: Mapped[bool] = mapped_column(Boolean, default=False)
    human_decision: Mapped[str | None] = mapped_column(String(30))
