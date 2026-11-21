from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

SYSTEM_MESSAGE = """
你是电商售后智能助手，负责处理与售后业务无关的闲聊。

要求：
1. 回复友好自然，最多两句话。
2. 不假装有个人经历、情感或实时信息。
3. 不承诺任何赔付结果，涉及售后一律引导用户提供订单号。
4. 每次回复自然引导回订单查询、售后申请或规则咨询。
""".strip()


class ChitchatAgent:

    def __init__(self):
        self.model = init_chat_model(
            model=settings.llm.chat_model,
            api_key=settings.llm.api_key,
            extra_body={"thinking": {"type": "disabled"}},
        )

    async def handle_chitchat(self, query: str) -> AIMessage:
        try:
            return await self.model.ainvoke(
                [
                    SystemMessage(content=SYSTEM_MESSAGE),
                    HumanMessage(content=query),
                ]
            )
        except Exception as e:
            logger.error(f"闲聊节点异常: {e}")
            return AIMessage("抱歉，我暂时无法回复，请稍后再试。")


chat = ChitchatAgent()
