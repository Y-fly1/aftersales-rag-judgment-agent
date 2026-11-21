from typing import Literal, NotRequired

from langgraph.graph import MessagesState

Intent = Literal[
    "after_sales",
    "order_query",
    "policy_qa",
    "chitchat",
    "human_handoff",
    "fallback",
]

INTENTS: tuple[str, ...] = (
    "after_sales",
    "order_query",
    "policy_qa",
    "chitchat",
    "human_handoff",
    "fallback",
)


class AfterSalesState(MessagesState):
    """售后智能体主图状态"""

    previous_workflow: NotRequired[Intent]
    active_workflow: NotRequired[Intent]
    # 本轮判责上下文
    order_no: NotRequired[str]
    ticket_id: NotRequired[str]
    verdict: NotRequired[dict]
    need_human: NotRequired[bool]
    decision: NotRequired[str]
