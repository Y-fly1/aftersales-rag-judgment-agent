from langchain.chat_models import init_chat_model
from langchain.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.agents.schemas import INTENTS
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """
你是电商售后智能体的意图识别节点，判断用户消息应交给哪个工作流。

intent 只能从以下选项中选择：
- after_sales：申请退款/退货/换货/维修，说商品有问题、破损、少件、不想要了
- order_query：查询订单状态、物流进度、签收时间
- policy_qa：咨询售后规则本身，例如"七天无理由怎么算""生鲜多久内可退"
- human_handoff：投诉、情绪激烈、要求人工客服、金额争议
- chitchat：与售后业务无关的闲聊
- fallback：无法判断
""".strip()


class IntentOutput(BaseModel):
    content: str


class IntentRouter:

    def __init__(self):
        self.model = init_chat_model(
            model=settings.llm.chat_model,
            api_key=settings.llm.api_key,
            extra_body={"thinking": {"type": "disabled"}},
        )
        self.with_model = self.model.with_structured_output(IntentOutput)

    async def route(self, query: str, context: str) -> str:
        try:
            response = await self.with_model.ainvoke(
                [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=f"用户消息：{query}\n上下文：{context}"),
                ]
            )
            intent = (response.content or "").strip()
            logger.info(f"意图识别结果: {intent}")
            return intent if intent in INTENTS else "fallback"
        except Exception as e:
            logger.error(f"意图识别失败: {e}")
            return "fallback"


intent_router = IntentRouter()
