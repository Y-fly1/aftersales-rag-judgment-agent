from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from typing import Literal


# 创建会话：前端POST发过来的数据长这样
class ChatThreadCreate(BaseModel):
    """创建会话请求"""

    title: str = Field(default="新会话", min_length=1, max_length=200)

    # 校验器：自动把标题前后空格删掉。比如用户输入"  我的会话  " → "我的会话"
    @field_validator("title", mode="before")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        return value.strip()


# 查询会话后，返回给前端的数据格式
class ChatThreadResponse(BaseModel):
    """会话响应"""

    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime



class ChatMessageResponse(BaseModel):
    """历史消息"""

    role: Literal["user", "assistant"]
    content: str


class ChatHistoryResponse(BaseModel):
    """会话历史响应"""

    thread_id: UUID
    messages: list[ChatMessageResponse]
