from uuid import UUID

from sqlalchemy import ARRAY, BigInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.models import Base, CreateAtMixin


class PolicyChunk(Base, CreateAtMixin):
    """政策父知识块：一个完整条款章节"""

    __tablename__ = "policy_chunks"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    policy_id: Mapped[int] = mapped_column(BigInteger)
    doc_name: Mapped[str] = mapped_column(String(300))
    section_path: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    content: Mapped[str] = mapped_column(Text)
