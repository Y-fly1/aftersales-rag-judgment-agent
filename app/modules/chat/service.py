import json

from fastapi.sse import ServerSentEvent
from langchain.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.chat.schemas import ChatRequest
from app.modules.chat_thread.exceptions import ChatThreadNotFoundError
from app.modules.chat_thread.repository import ChatThreadRepository


class ChatService:

    def __init__(self, session: AsyncSession, agent: CompiledStateGraph):
        self.repository = ChatThreadRepository(session)
        self.agent = agent

    async def chat_stream(self, user_id: int, request: ChatRequest):
        # 1. 校验会话归属
        thread = await self.repository.find_thread(request.thread_id, user_id)
        if thread is None:
            raise ChatThreadNotFoundError

        config = {
            "configurable": {
                "thread_id": str(request.thread_id),
                # 判责节点需要用户身份，透传到图内部
                "user_id": user_id,
            }
        }

        if request.decision is not None:
            _input = Command(resume=request.decision)
        else:
            _input = {"messages": [HumanMessage(content=request.message or "")]}

        # 2. 流式输出文本增量
        result = await self.agent.astream_events(_input, config, version="v3")
        async for message in result.messages:
            async for text in message.text:
                yield ServerSentEvent(data=text, event="message")

        # 3. 图若停在 interrupt（人工审批），把待审批内容透给前端
        snapshot = await self.agent.aget_state(config)
        if snapshot.interrupts:
            payload = snapshot.interrupts[0].value
            yield ServerSentEvent(
                data=json.dumps(payload, ensure_ascii=False, default=str),
                event="interrupt",
            )

        yield ServerSentEvent(data="[DONE]", event="done")
