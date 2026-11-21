"""售后判责规则引擎

设计原则：判责结论不交给 LLM。
规则覆盖 90% 的常规情形，输出可复现的责任方、动作、金额与政策依据；
LLM 只负责「把用户口语转成结构化诉求」和「把结论翻译成人话」。
规则未命中时置信度为 low，一律转人工，避免模型自由发挥造成资损。
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

# ---- 阈值与费用标准（均可配置化）----
RETURN_WINDOW_DAYS = 7
FRESH_WINDOW_HOURS = 48
HUMAN_REVIEW_AMOUNT = Decimal("1000")
LARGE_RETURN_LOGISTICS_FEE = Decimal("200")
INSTALL_SERVICE_FEE = Decimal("150")

# ---- 政策编号 ----
POLICY_RETURN = "PL-RET-001"
POLICY_QUALITY = "PL-QUA-002"
POLICY_LOGISTICS = "PL-LOG-003"
POLICY_FRESH = "PL-FRS-004"
POLICY_LARGE = "PL-LRG-005"


@dataclass(frozen=True)
class OrderFacts:
    """判责所需的订单事实，与 ORM 解耦便于单测"""

    order_no: str
    category: str
    amount: Decimal
    status: str
    logistics_status: str | None = None
    delivered_at: datetime | None = None
    is_custom: bool = False
    is_fresh: bool = False
    is_large: bool = False
    is_installed: bool = False
    is_digital: bool = False


@dataclass(frozen=True)
class Claim:
    """结构化的售后诉求"""

    type: str = "refund"  # refund / return / exchange / repair / complaint
    reason: str = "no_reason"  # quality / no_reason / damaged / missing / not_as_described
    description: str = ""


@dataclass(frozen=True)
class Verdict:
    liable_party: str
    action: str
    amount: Decimal
    confidence: str
    policy_nos: list[str] = field(default_factory=list)
    reasoning: str = ""
    need_human: bool = False
    days_since_delivery: int | None = None


def days_since(delivered_at: datetime | None, now: datetime) -> int | None:
    if delivered_at is None:
        return None
    # 数据库里可能是 naive datetime（psycopg 返回带时区则不会），统一按 UTC 处理
    if delivered_at.tzinfo is None:
        delivered_at = delivered_at.replace(tzinfo=timezone.utc)
    delta = now - delivered_at
    return max(delta.days, 0)


def judge(
    order: OrderFacts,
    claim: Claim,
    now: datetime | None = None,
) -> Verdict:
    """对单个售后诉求给出确定性判责结论"""
    now = now or datetime.now(timezone.utc)
    days = days_since(order.delivered_at, now)
    amount = Decimal(order.amount)

    def verdict(
        liable_party: str,
        action: str,
        action_amount: Decimal,
        confidence: str,
        policy_nos: list[str],
        reasoning: str,
    ) -> Verdict:
        need_human = (
            confidence == "low"
            or action == "manual"
            or action_amount >= HUMAN_REVIEW_AMOUNT
        )
        return Verdict(
            liable_party=liable_party,
            action=action,
            amount=action_amount.quantize(Decimal("0.01")),
            confidence=confidence,
            policy_nos=policy_nos,
            reasoning=reasoning,
            need_human=need_human,
            days_since_delivery=days,
        )

    # R0 投诉类不进自动判责
    if claim.type == "complaint":
        return verdict(
            "unknown", "manual", Decimal("0"), "low", [],
            "投诉类诉求涉及服务态度或纠纷升级，转人工处理。",
        )

    # R1 运输破损 / 丢件：承运方责任，商家先行赔付
    if claim.reason in ("damaged", "missing"):
        logistics_hint = order.logistics_status or ""
        if order.status == "shipped" or "破损" in logistics_hint or "丢" in logistics_hint or claim.reason == "missing":
            action = "reship" if claim.type in ("exchange", "return") else "full_refund"
            return verdict(
                "logistics", action, amount, "high", [POLICY_LOGISTICS],
                f"物流状态为「{logistics_hint or '运输中'}」，属于运输环节破损/丢件，"
                "由承运方承担责任，商家先行赔付后向物流追偿。",
            )

    # R2 生鲜腐坏：48 小时内全额退款，无需退回
    if order.is_fresh and claim.reason in ("quality", "damaged"):
        if days is not None and days * 24 <= FRESH_WINDOW_HOURS:
            return verdict(
                "merchant", "full_refund", amount, "high", [POLICY_FRESH],
                f"生鲜商品签收 {days} 天，在 48 小时售后时效内且属腐坏变质，"
                "按生鲜规则全额退款且无需退回商品。",
            )
        return verdict(
            "unknown", "manual", Decimal("0"), "low", [POLICY_FRESH],
            f"生鲜商品已签收超过 {FRESH_WINDOW_HOURS} 小时，超出规则时效，需人工核实照片凭证。",
        )

    # R3 质量问题 / 与描述不符：不受七天限制
    if claim.reason in ("quality", "not_as_described"):
        action_map = {"repair": "repair", "exchange": "exchange"}
        action = action_map.get(claim.type, "full_refund")
        return verdict(
            "merchant", action, amount, "high", [POLICY_QUALITY],
            "属于商品质量问题，不受七天无理由期限限制，商家承担来回运费并退换修。"
            "需用户补充问题凭证照片。",
        )

    # R4 定制商品不适用无理由
    if order.is_custom and claim.reason == "no_reason":
        return verdict(
            "buyer", "reject", Decimal("0"), "high", [POLICY_RETURN],
            "该订单为定制商品，按规则不适用七天无理由退货；"
            "若无质量问题，无法支持无理由退款。",
        )

    # R5 数字化商品不适用无理由
    if order.is_digital and claim.reason == "no_reason":
        return verdict(
            "buyer", "reject", Decimal("0"), "high", [POLICY_RETURN],
            "数字化商品一经交付不适用七天无理由退货。",
        )

    # R6 生鲜不适用无理由
    if order.is_fresh and claim.reason == "no_reason":
        return verdict(
            "buyer", "reject", Decimal("0"), "high", [POLICY_RETURN, POLICY_FRESH],
            "生鲜易腐商品不适用七天无理由退货，仅在腐坏变质时按生鲜规则赔付。",
        )

    # R7 尚未签收，事实不全，转人工
    if order.status != "delivered" or days is None:
        return verdict(
            "unknown", "manual", Decimal("0"), "low", [],
            "订单尚未签收或缺少签收时间，无法计算售后时效，转人工核实物流状态。",
        )

    # R8 七天无理由：大件已安装需扣物流与安装费
    if claim.reason == "no_reason" and days <= RETURN_WINDOW_DAYS:
        if order.is_large and order.is_installed:
            deduction = LARGE_RETURN_LOGISTICS_FEE + INSTALL_SERVICE_FEE
            refund = max(amount - deduction, Decimal("0"))
            return verdict(
                "buyer", "partial_refund", refund, "medium", [POLICY_RETURN, POLICY_LARGE],
                f"签收 {days} 天在七天无理由期内，但大件商品已安装，"
                f"需扣除往返物流费 {LARGE_RETURN_LOGISTICS_FEE} 元与拆装费 {INSTALL_SERVICE_FEE} 元。",
            )
        return verdict(
            "buyer", "full_refund", amount, "medium", [POLICY_RETURN],
            f"签收 {days} 天，在七天无理由期内且商品完好，支持退货退款，退回运费由买家承担。",
        )

    # R9 超过七天且无质量问题
    if claim.reason == "no_reason":
        return verdict(
            "buyer", "reject", Decimal("0"), "medium", [POLICY_RETURN],
            f"签收已 {days} 天，超过七天无理由期限，且未主张质量问题，无法支持退货退款。",
        )

    # R10 兜底
    return verdict(
        "unknown", "manual", Decimal("0"), "low", [],
        "诉求信息不足，无法匹配现有规则，转人工处理。",
    )
