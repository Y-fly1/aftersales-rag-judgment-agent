from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .models import ChatThread


class ChatThreadRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    # 添加会话的SQL语句
    async def add(self, chat_thread: ChatThread):
        self.session.add(chat_thread)

    # 查询会话列表的SQL语句
    async def get_list(self, user_id):
        result = await self.session.scalars(
            select(ChatThread)
            .where(ChatThread.user_id == user_id)
            .order_by(ChatThread.created_at.desc())
        )
        return result.all()

    # 查询会话的SQL语句
    async def find_thread(self, thread_id, user_id):
        chat_thread = await self.session.scalar(
            select(ChatThread)
            .where(ChatThread.user_id == user_id)
            .where(ChatThread.id == thread_id)
        )
        return chat_thread

    # 删除会话的SQL语句
    async def delete_chat(self, thread: ChatThread) -> None:
        await self.session.delete(thread)
