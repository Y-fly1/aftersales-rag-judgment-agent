from datetime import datetime
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.ext.asyncio import AsyncSession
from .repository import ChatThreadRepository
from .models import ChatThread
from app.modules.chat_thread.exceptions import ChatThreadNotFoundError

from uuid import UUID

from langchain.messages import AIMessage, HumanMessage

from app.modules.chat_thread.schemas import (
    ChatHistoryResponse,
    ChatMessageResponse,
)


async def get_history(
    self,
    thread_id: UUID,
    user_id: int,
) -> ChatHistoryResponse:
    # 1.校验会话归属
    thread = await self.repository.find_owned(thread_id, user_id)
    if thread is None:
        raise ChatThreadNotFoundError

    # 2.读取Agent最新快照
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = await self.agent.aget_state(config)

    # 3.只保留用户消息和AI消息
    messages = []
    for message in snapshot.values.get("messages", []):
        if isinstance(message, HumanMessage):
            role = "user"
        elif isinstance(message, AIMessage):
            role = "assistant"
        else:
            continue

        if message.text:
            messages.append(
                ChatMessageResponse(
                    role=role,
                    content=message.text,
                )
            )

    return ChatHistoryResponse(
        thread_id=thread_id,
        messages=messages,
    )



class ChatThreadService:
    # 创建service时就进行的初始化，绑定session和repository
    def __init__(self,
                 session: AsyncSession,
                 agent: CompiledStateGraph
                 ):
        self.session = session
        self.repository = ChatThreadRepository(session)
        self.agent = agent

    # 添加会话方法
    async def add_chat(self, title: str, user_id: int):
        # 用上下文管理，开启事务，运行完成，自动commit，出现异常，自动rollback
        async with self.session.begin():
            # 创建对象，对象 映射 到数据库 一条数据(对传来的参数进行封装，创建对象，准备插入数据库)
            chat_thread = ChatThread(user_id=user_id, title=title)
            # 新增对象，就是插入一条数据(将对象插入数据库，具体执行插入操作由repository完成)
            await self.repository.add(chat_thread)
            return chat_thread

    # 获取会话列表方法
    async def get_list(self, user_id):
        return await self.repository.get_list(user_id)

    # 重命名会话方法
    async def rename_chat(self, thread_id, title, user_id):
        # 用上下文管理，开启事务，运行完成，自动commit，出现异常，自动rollback
        async with self.session.begin():
            # 检查会话是否存在
            # 这一步仅仅是查是否存在，有了就给chat_thread变量，没有就报错
            chat_thread = await self.repository.find_thread(thread_id, user_id)
            # 如果不存在，报异常
            if not chat_thread:
                raise ChatThreadNotFoundError
            # 如果存在，修改chat_thread变量里的title，updated_at
            chat_thread.title = title
            chat_thread.updated_at = datetime.now()
        return chat_thread

    # 获取删除会话方法
    async def delete_chat(self, thread_id, user_id):
        # 用上下文管理，开启事务，运行完成，自动commit，出现异常，自动rollback
        async with self.session.begin():
            # 检查会话是否存在
            # 这一步仅仅是查是否存在，有了就给chat_thread变量，没有就报错
            chat_thread = await self.repository.find_thread(thread_id, user_id)
            # 如果不存在，报异常
            if not chat_thread:
                raise ChatThreadNotFoundError

            # 2.删除Checkpointer中的会话状态
            await self.agent.checkpointer.adelete_thread(str(thread_id))
            # 如果存在调用repository的删除方法
            await self.repository.delete_chat(chat_thread)

    async def get_history(
            self,
            thread_id: UUID,
            user_id: int,
    ) -> ChatHistoryResponse:
        # 1.校验会话归属
        thread = await self.repository.find_thread(thread_id, user_id)
        if thread is None:
            raise ChatThreadNotFoundError

        # 2.读取Agent最新快照
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = await self.agent.aget_state(config)

        # 3.只保留用户消息和AI消息
        messages = []
        for message in snapshot.values.get("messages", []):
            if isinstance(message, HumanMessage):
                role = "user"
            elif isinstance(message, AIMessage):
                role = "assistant"
            else:
                continue

            if message.text:
                messages.append(
                    ChatMessageResponse(
                        role=role,
                        content=message.text,
                    )
                )

        return ChatHistoryResponse(
            thread_id=thread_id,
            messages=messages,
        )