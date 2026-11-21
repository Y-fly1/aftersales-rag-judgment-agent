from datetime import date

from sqlalchemy import ARRAY, BigInteger, Date, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.common.models import Base, CreateAtMixin, UpdateAtMixin


class Policy(Base, CreateAtMixin, UpdateAtMixin):
    """售后政策 / 平台规则"""

    __tablename__ = "policies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    policy_no: Mapped[str] = mapped_column(String(50), unique=True)
    title: Mapped[str] = mapped_column(String(300))
    doc_name: Mapped[str] = mapped_column(String(300))
    category: Mapped[str] = mapped_column(String(50))
    scope: Mapped[str | None] = mapped_column(String(200))
    effective_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="in_force")
    summary: Mapped[str | None] = mapped_column(Text)
    highlights: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
