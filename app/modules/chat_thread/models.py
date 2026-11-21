from uuid import UUID, uuid4
from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.common.models import Base, CreateAtMixin, UpdateAtMixin


class ChatThread(Base, CreateAtMixin, UpdateAtMixin):
    """客服会话"""
# `CreateAtMixin`、`UpdateAtMixin`是继承来的
# 自动带上`created_at`创建时间、`updated_at`更新时间字段，不用自己重复写。
    __tablename__ = "chat_threads"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    user_id: Mapped[int] = mapped_column(Integer)

    title: Mapped[str] = mapped_column(
        String(200),
        default="新会话",
    )
