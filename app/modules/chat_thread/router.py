from typing import Annotated
from fastapi import APIRouter, Depends, Header, Response, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.infra.database import get_session
from .schemas import *
from .service import ChatThreadService
from uuid import UUID
from app.modules.chat_thread.schemas import ChatHistoryResponse

router = APIRouter(prefix="/api/v1/chat-threads", tags=["会话管理的接口"])


def get_service(request: Request,
                session: AsyncSession = Depends(get_session)):
    return ChatThreadService(session=session,
                             agent=request.app.state.agent)


# 创建新会话的接口
@router.post("", response_model=ChatThreadResponse)
async def create_chat_thread(
        request_body: ChatThreadCreate,
        user_id: Annotated[int, Header(alias="x-user-id")],
        service: ChatThreadService = Depends(get_service)
):
    return await service.add_chat(request_body.title, user_id)


# 获取会话列表的接口
@router.get("", response_model=list[ChatThreadResponse])
async def get_chat_thread_list(
        user_id: Annotated[int, Header(alias="x-user-id")],
        service: ChatThreadService = Depends(get_service)
):
    return await service.get_list(user_id)


# 重命名会话列表的接口
@router.patch("/{thread_id}", response_model=ChatThreadResponse)
async def rename_chat_thread(
        thread_id: str,
        result_body: ChatThreadCreate,
        user_id: Annotated[int, Header(alias="x-user-id")],
        service: ChatThreadService = Depends(get_service)
):
    return await service.rename_chat(thread_id, result_body.title, user_id)


# 删除会话的接口
@router.delete("/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
        thread_id: UUID,
        user_id: Annotated[int, Header(alias="x-user-id")],
        service: ChatThreadService = Depends(get_service)
):
    await service.delete_chat(thread_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{thread_id}/messages", response_model=ChatHistoryResponse)
async def get_chat_history(
        thread_id: UUID,
        user_id: Annotated[int, Header(alias="x-user-id")],
        service: ChatThreadService = Depends(get_service),
):
    """查询指定会话的历史消息"""

    return await service.get_history(thread_id, user_id)
