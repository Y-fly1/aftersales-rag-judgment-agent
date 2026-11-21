"""把用户口语转成结构化售后诉求

LLM 只做「理解」，不做「判责」。抽取失败时用正则兜底，
保证没有模型也能跑通主链路。
"""

import re
from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_core.messages import BaseMessage, HumanMessage
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

ORDER_NO_PATTERN = re.compile(r"\b(AS\d{8,})\b", re.IGNORECASE)

SYSTEM_PROMPT = """
你是售后工单的信息抽取器。从用户对话中抽取出申请售后所必需的信息。

字段说明：
- order_no：订单号，形如 AS20261110001；用户没提到就返回 null，不要编造。
- type：诉求类型，refund 退款 / return 退货 / exchange 换货 / repair 维修 / complaint 投诉。
- reason：诉求原因，quality 质量问题 / damaged 运输破损或丢件 / missing 少件漏发 /
  not_as_described 与描述不符 / no_reason 单纯不想要（无理由）。

判断原则：用户说"坏了、有异味、用不了、是假货"归 quality；说"摔碎了、箱子破了、没收到"归 damaged 或 missing；
只说"不想要了、买错了、七天无理由"归 no_reason。
""".strip()


class ClaimExtraction(BaseModel):
    order_no: str | None = Field(default=None, description="订单号，无则 null")
    type: Literal["refund", "return", "exchange", "repair", "complaint"] = "refund"
    reason: Literal["quality", "damaged", "missing", "not_as_described", "no_reason"] = "no_reason"


class ClaimExtractor:

    def __init__(self):
        self.model = init_chat_model(
            model=settings.llm.chat_model,
            api_key=settings.llm.api_key,
            extra_body={"thinking": {"type": "disabled"}},
        )
        self.with_model = self.model.with_structured_output(ClaimExtraction)

    async def extract(self, messages: list[BaseMessage]) -> ClaimExtraction:
        # 对话只取最近 6 条，避免长历史干扰抽取
        recent = messages[-6:]
        transcript = "\n".join(
            f"{'用户' if isinstance(m, HumanMessage) else '客服'}：{m.text or ''}"
            for m in recent
            if getattr(m, "text", None)
        )

        try:
            result = await self.with_model.ainvoke(
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": transcript},
                ]
            )
        except Exception as e:
            logger.error(f"诉求抽取失败，降级为正则: {e}")
            result = ClaimExtraction()

        # 正则兜底：模型没抽到订单号时，从原文再捞一次
        if not result.order_no:
            matched = ORDER_NO_PATTERN.search(transcript.upper())
            if matched:
                result.order_no = matched.group(1)
        return result


extractor = ClaimExtractor()
