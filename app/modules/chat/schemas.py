from uuid import UUID

from pydantic import BaseModel, model_validator


class ChatRequest(BaseModel):
    """对话请求：普通消息，或对中断审批的决策回复"""

    thread_id: UUID
    message: str | None = None
    decision: dict | None = None

    @model_validator(mode="after")
    def require_message_or_decision(self) -> "ChatRequest":
        if not self.message and self.decision is None:
            raise ValueError("message 与 decision 至少提供一个")
        return self
