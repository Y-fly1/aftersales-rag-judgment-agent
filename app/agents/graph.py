from functools import partial
from typing import Literal
from uuid import UUID

from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from app.agents.chitchat import chat
from app.agents.extraction import ORDER_NO_PATTERN, extractor
from app.agents.intent_router import intent_router
from app.agents.policy_advisor import init_policy_advisor
from app.agents.schemas import AfterSalesState
from app.infra.database import AsyncSessionFactory
from app.modules.order.exceptions import OrderNotFoundError
from app.modules.order.service import OrderService
from app.modules.ticket.schemas import ApprovalRequest, TicketCreate
from app.modules.ticket.service import TicketService

PARTY_LABELS = {
    "merchant": "商家",
    "logistics": "物流方",
    "buyer": "买家",
    "unknown": "待确认",
}
ACTION_LABELS = {
    "full_refund": "全额退款",
    "partial_refund": "部分退款",
    "exchange": "换货",
    "repair": "维修",
    "reject": "不支持退款",
    "reship": "补发商品",
    "manual": "转人工处理",
}
STATUS_LABELS = {
    "paid": "已付款待发货",
    "shipped": "已发货运输中",
    "delivered": "已签收",
    "closed": "已关闭",
    "refunded": "已退款",
}


def _user_id(config: RunnableConfig) -> int | None:
    return (config.get("configurable") or {}).get("user_id")


# ============ 路由 ============

# 意图 → 节点名（after_sales 落到判责节点）
NodeName = Literal[
    "after_sales_judge",
    "order_query",
    "policy_qa",
    "chitchat",
    "human_handoff",
    "fallback",
]

INTENT_NODES: dict[str, NodeName] = {
    "after_sales": "after_sales_judge",
    "order_query": "order_query",
    "policy_qa": "policy_qa",
    "chitchat": "chitchat",
    "human_handoff": "human_handoff",
    "fallback": "fallback",
}


async def route_node(state: AfterSalesState) -> Command[NodeName]:
    previous = state.get("active_workflow", "")
    previous_reply = _find_previous_ai_message(state.get("messages"))
    context = f"上一轮回复：{previous_reply}；上一轮节点：{previous}"

    result = await intent_router.route(state.get("messages")[-1].content, context)
    return Command(
        update={"previous_workflow": previous, "active_workflow": result},
        goto=INTENT_NODES.get(result, "fallback"),
    )


# ============ 判责主链路 ============

async def after_sales_judge_node(state: AfterSalesState, config: RunnableConfig) -> dict:
    """抽取诉求 → 查订单 → 规则判责 → 落工单。LLM 只参与第一步。"""
    user_id = _user_id(config)
    if user_id is None:
        return {"messages": [AIMessage("请先登录后再申请售后。")]}

    # 中断恢复时会重跑本节点，已判过就直接跳过，避免重复建单
    if state.get("ticket_id"):
        return {}

    extraction = await extractor.extract(state["messages"])
    order_no = extraction.order_no
    if not order_no:
        return {
            "messages": [
                AIMessage("请提供订单号（形如 AS20261110001），我才能核对订单事实并判定责任。")
            ]
        }

    async with AsyncSessionFactory() as session:
        service = TicketService(session)
        try:
            ticket, verdict = await service.create_and_judge(
                user_id,
                TicketCreate(
                    order_no=order_no,
                    type=extraction.type,
                    reason=extraction.reason,
                ),
            )
        except OrderNotFoundError:
            return {
                "messages": [
                    AIMessage(f"没有查到你名下的订单 {order_no}，请核对后重新提供。")
                ]
            }

    return {
        "order_no": order_no,
        "ticket_id": str(ticket.id),
        "need_human": ticket.need_human,
        "verdict": {
            "liable_party": verdict.liable_party,
            "action": verdict.action,
            "amount": str(verdict.amount),
            "confidence": verdict.confidence,
            "policy_refs": ticket.policy_refs,
            "reasoning": verdict.reasoning,
            "days_since_delivery": verdict.days_since_delivery,
        },
    }


async def approve_node(state: AfterSalesState, config: RunnableConfig) -> dict:
    """金额超阈值或置信度低时暂停，等人工审批"""
    payload = interrupt(
        {
            "type": "approval",
            "ticket_id": state.get("ticket_id"),
            "order_no": state.get("order_no"),
            "verdict": state.get("verdict"),
            "message": "该笔售后需要人工审批，请确认是否执行。",
        }
    )

    decision = payload.get("decision") if isinstance(payload, dict) else str(payload)
    if decision not in ("approved", "rejected"):
        decision = "rejected"

    user_id = _user_id(config)
    ticket_id = state.get("ticket_id")
    if user_id is not None and ticket_id:
        async with AsyncSessionFactory() as session:
            await TicketService(session).approve(
                UUID(ticket_id),
                user_id,
                ApprovalRequest(decision=decision),
            )
    return {"decision": decision}


async def respond_node(state: AfterSalesState) -> dict:
    """用模板渲染结论，防止 LLM 改写判责结果造成资损"""
    return {"messages": [AIMessage(_render_verdict(state))]}


def _render_verdict(state: AfterSalesState) -> str:
    verdict = state.get("verdict") or {}
    party = PARTY_LABELS.get(verdict.get("liable_party", "unknown"), "待确认")
    action = ACTION_LABELS.get(verdict.get("action", "manual"), "转人工处理")
    amount = verdict.get("amount") or "0"
    confidence = {"high": "高", "medium": "中", "low": "低"}.get(
        verdict.get("confidence", ""), "未知"
    )
    days = verdict.get("days_since_delivery")

    head = f"【判责结论】责任方：{party}｜处置：{action}"
    if amount not in ("0", "0.00", ""):
        head += f" ¥{amount}"
    head += f"｜置信度：{confidence}"

    lines = [head]
    refs = verdict.get("policy_refs") or []
    if refs:
        lines.append(
            "依据：" + "、".join(f"《{ref.get('title') or ref['policy_no']}》{ref['policy_no']}" for ref in refs)
        )
    if days is not None:
        lines.append(f"签收时长：{days} 天")
    lines.append(f"说明：{verdict.get('reasoning') or ''}")

    if state.get("need_human"):
        decision = state.get("decision")
        if decision == "approved":
            lines.append("✅ 人工审批已通过，退款/换货将在 1-3 个工作日内处理。")
        elif decision == "rejected":
            lines.append("❌ 人工审批未通过，本单售后申请已关闭。如需复议请联系人工客服。")
        else:
            lines.append("⏳ 该单已进入人工审批队列。")
    else:
        lines.append("✅ 该单已按规则自动执行，无需人工介入。")

    lines.append(f"工单号：{state.get('ticket_id', '-')}")
    return "\n".join(lines)


# ============ 其他工作流 ============

async def order_query_node(state: AfterSalesState, config: RunnableConfig) -> dict:
    user_id = _user_id(config)
    text = state.get("messages")[-1].content or ""
    matched = ORDER_NO_PATTERN.search(text.upper())
    if not matched:
        return {"messages": [AIMessage("请提供订单号（形如 AS20261110001），我帮你查物流和签收时间。")]}

    order_no = matched.group(1)
    async with AsyncSessionFactory() as session:
        try:
            order = await OrderService(session).get_order(order_no, user_id or 0)
        except OrderNotFoundError:
            return {"messages": [AIMessage(f"没有查到你名下的订单 {order_no}。")]}

    delivered = order.delivered_at.strftime("%Y-%m-%d %H:%M") if order.delivered_at else "未签收"
    return {
        "messages": [
            AIMessage(
                f"订单 {order.order_no}｜{order.product_name}\n"
                f"金额 ¥{order.amount}｜状态：{STATUS_LABELS.get(order.status, order.status)}\n"
                f"物流：{order.logistics_status or '无'}（{order.logistics_no or '-'}）\n"
                f"签收时间：{delivered}\n"
                "需要申请售后的话，直接告诉我遇到的问题即可。"
            )
        ]
    }


async def policy_qa_node(state: AfterSalesState, advisor) -> dict:
    result = await advisor.ainvoke({"messages": state["messages"]})
    return {"messages": [result["messages"][-1]]}


async def chitchat_node(state: AfterSalesState) -> dict:
    response = await chat.handle_chitchat(state.get("messages")[-1].content)
    return {"messages": [response]}


async def human_handoff_node(state: AfterSalesState) -> dict:
    return {
        "messages": [
            AIMessage(
                "已为你转接人工客服，工作时间内 5 分钟内响应。\n"
                "如果涉及金额争议，请保留订单号与问题凭证，客服会直接调取本次判责记录。"
            )
        ]
    }


async def fallback_node(state: AfterSalesState) -> dict:
    return {
        "messages": [
            AIMessage(
                "没太理解你的诉求。你可以：\n"
                "1. 发订单号查物流（如 AS20261110001）\n"
                "2. 直接说遇到的问题，例如「耳机有杂音想退货」\n"
                "3. 问规则，例如「生鲜多久内可以申请售后」"
            )
        ]
    }


def _find_previous_ai_message(messages: list[BaseMessage]) -> str:
    for message in reversed(messages[:-1]):
        if not isinstance(message, AIMessage):
            continue
        if message.tool_calls:
            continue
        if message.text:
            return message.text
    return ""


def _next_after_judge(state: AfterSalesState) -> str:
    """没拿到订单号时节点已直接回复用户，不应再进渲染节点"""
    if not state.get("ticket_id"):
        return "end"
    return "approve" if state.get("need_human") else "respond"


# ============ 组装主图 ============

def init_after_sales_graph(checkpointer: AsyncPostgresSaver):
    advisor = init_policy_advisor()

    builder = StateGraph(AfterSalesState)
    builder.add_node("route", route_node)
    builder.add_node("after_sales_judge", after_sales_judge_node)
    builder.add_node("approve", approve_node)
    builder.add_node("respond", respond_node)
    builder.add_node("order_query", order_query_node)
    builder.add_node("policy_qa", partial(policy_qa_node, advisor=advisor))
    builder.add_node("chitchat", chitchat_node)
    builder.add_node("human_handoff", human_handoff_node)
    builder.add_node("fallback", fallback_node)

    builder.add_edge(START, "route")

    # 判责后：需人工 → 中断审批 → 输出；否则直接输出
    builder.add_conditional_edges(
        "after_sales_judge",
        _next_after_judge,
        {"approve": "approve", "respond": "respond", "end": END},
    )
    builder.add_edge("approve", "respond")

    for node in ("respond", "order_query", "policy_qa", "chitchat", "human_handoff", "fallback"):
        builder.add_edge(node, END)

    return builder.compile(checkpointer=checkpointer)
