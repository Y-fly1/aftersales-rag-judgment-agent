from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

from app.agents.tools import search_policies, search_policy_article
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

POLICY_SYSTEM_PROMPT = """
你是电商平台的售后规则顾问，负责解释售后政策条款。

规则：
1. 回答前必须先调用 search_policies 定位政策，再调用 search_policy_article 取原文。
2. 必须写明依据，格式为「《政策标题》政策编号 PL-XXX-000」。
3. 严禁编造条款、时效或费率；检索不到就如实说明，并建议转人工。
4. 区分「平台强制规则」和「商家自行承诺」，冲突时以更有利于消费者的为准，并说明这一点。
5. 回答控制在 3 句话以内，结论先行，最后一句给出用户下一步该做什么。
6. 不要替用户判定具体订单的责任——那需要订单事实，引导用户提供订单号走售后申请。
"""


def init_policy_advisor():
    """带政策检索工具的规则问答 Agent"""
    model = init_chat_model(
        model=settings.llm.chat_model,
        model_provider="deepseek",
        api_key=settings.llm.api_key,
        extra_body={"thinking": {"type": "disabled"}},
    )
    agent = create_agent(
        model=model,
        tools=[search_policies, search_policy_article],
        system_prompt=POLICY_SYSTEM_PROMPT,
    )
    logger.info("政策问答 Agent 初始化成功✅️")
    return agent
