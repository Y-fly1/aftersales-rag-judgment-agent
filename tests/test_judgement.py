"""判责规则引擎回归测试

规则是资损防线，必须可测、可回归。运行：uv run pytest -q
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.agents.judgement import Claim, OrderFacts, judge

NOW = datetime(2026, 11, 21, 10, 0, tzinfo=timezone.utc)


def make_order(**kwargs) -> OrderFacts:
    base = dict(
        order_no="AS20261110001",
        category="general",
        amount=Decimal("299.00"),
        status="delivered",
        logistics_status="已签收",
        delivered_at=NOW - timedelta(days=3),
    )
    base.update(kwargs)
    return OrderFacts(**base)


def test_fresh_rotten_within_48h_full_refund():
    verdict = judge(
        make_order(
            category="fresh",
            is_fresh=True,
            amount=Decimal("168.00"),
            delivered_at=NOW - timedelta(days=1),
        ),
        Claim(type="refund", reason="quality"),
        NOW,
    )
    assert verdict.liable_party == "merchant"
    assert verdict.action == "full_refund"
    assert verdict.amount == Decimal("168.00")
    assert verdict.confidence == "high"
    assert "PL-FRS-004" in verdict.policy_nos


def test_fresh_rotten_beyond_48h_goes_to_human():
    verdict = judge(
        make_order(is_fresh=True, delivered_at=NOW - timedelta(days=4)),
        Claim(type="refund", reason="quality"),
        NOW,
    )
    assert verdict.need_human is True
    assert verdict.confidence == "low"


def test_custom_product_no_reason_rejected():
    verdict = judge(
        make_order(is_custom=True, amount=Decimal("899.00")),
        Claim(type="refund", reason="no_reason"),
        NOW,
    )
    assert verdict.liable_party == "buyer"
    assert verdict.action == "reject"
    assert verdict.amount == Decimal("0.00")


def test_digital_product_no_reason_rejected():
    verdict = judge(
        make_order(is_digital=True),
        Claim(type="refund", reason="no_reason"),
        NOW,
    )
    assert verdict.action == "reject"


def test_quality_issue_not_limited_by_seven_days():
    verdict = judge(
        make_order(delivered_at=NOW - timedelta(days=12)),
        Claim(type="refund", reason="quality"),
        NOW,
    )
    assert verdict.liable_party == "merchant"
    assert verdict.action == "full_refund"
    assert verdict.confidence == "high"


def test_logistics_damage_before_delivery():
    verdict = judge(
        make_order(
            status="shipped",
            logistics_status="运输破损待拒收",
            delivered_at=None,
        ),
        Claim(type="refund", reason="damaged"),
        NOW,
    )
    assert verdict.liable_party == "logistics"
    assert "PL-LOG-003" in verdict.policy_nos
    assert verdict.confidence == "high"


def test_normal_no_reason_within_seven_days():
    verdict = judge(
        make_order(amount=Decimal("299.00")),
        Claim(type="refund", reason="no_reason"),
        NOW,
    )
    assert verdict.action == "full_refund"
    assert verdict.confidence == "medium"
    # 299 元未超阈值，自动执行
    assert verdict.need_human is False


def test_large_installed_deduction_and_human_review():
    verdict = judge(
        make_order(is_large=True, is_installed=True, amount=Decimal("3299.00")),
        Claim(type="refund", reason="no_reason"),
        NOW,
    )
    assert verdict.action == "partial_refund"
    assert verdict.amount == Decimal("2949.00")
    assert verdict.need_human is True


def test_no_reason_beyond_seven_days_rejected():
    verdict = judge(
        make_order(delivered_at=NOW - timedelta(days=9)),
        Claim(type="refund", reason="no_reason"),
        NOW,
    )
    assert verdict.action == "reject"
    assert "PL-RET-001" in verdict.policy_nos


def test_complaint_always_manual():
    verdict = judge(
        make_order(),
        Claim(type="complaint", reason="no_reason"),
        NOW,
    )
    assert verdict.action == "manual"
    assert verdict.need_human is True


def test_order_not_delivered_falls_back_to_manual():
    verdict = judge(
        make_order(status="paid", delivered_at=None),
        Claim(type="refund", reason="no_reason"),
        NOW,
    )
    assert verdict.action == "manual"
    assert verdict.confidence == "low"
