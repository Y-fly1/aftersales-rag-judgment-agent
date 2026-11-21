from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.judgement import Claim, OrderFacts, Verdict, judge
from app.modules.order.exceptions import OrderNotFoundError
from app.modules.order.repository import OrderRepository
from app.modules.policy.repository import PolicyRepository
from app.modules.ticket.exceptions import TicketNotFoundError, TicketStateError
from app.modules.ticket.models import Ticket
from app.modules.ticket.repository import TicketRepository
from app.modules.ticket.schemas import ApprovalRequest, TicketCreate


class TicketService:

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = TicketRepository(session)
        self.orders = OrderRepository(session)
        self.policies = PolicyRepository(session)

    async def create_and_judge(self, user_id: int, payload: TicketCreate) -> tuple[Ticket, Verdict]:
        order = await self.orders.get_by_order_no(payload.order_no, user_id)
        if order is None:
            raise OrderNotFoundError

        facts = OrderFacts(
            order_no=order.order_no,
            category=order.category,
            amount=order.amount,
            status=order.status,
            logistics_status=order.logistics_status,
            delivered_at=order.delivered_at,
            is_custom=order.is_custom,
            is_fresh=order.is_fresh,
            is_large=order.is_large,
            is_installed=order.is_installed,
            is_digital=order.is_digital,
        )
        verdict = judge(
            facts,
            Claim(
                type=payload.type,
                reason=payload.reason,
                description=payload.description or "",
            ),
        )

        refs = await self._build_policy_refs(verdict.policy_nos)
        ticket = Ticket(
            user_id=user_id,
            order_no=order.order_no,
            type=payload.type,
            reason=payload.reason,
            description=payload.description,
            status="pending_approval" if verdict.need_human else "executed",
            liable_party=verdict.liable_party,
            action=verdict.action,
            action_amount=verdict.amount,
            confidence=verdict.confidence,
            policy_refs=refs,
            reasoning=verdict.reasoning,
            need_human=verdict.need_human,
        )
        async with self.session.begin():
            self.repository.add(ticket)
        return ticket, verdict

    async def list_tickets(self, user_id: int) -> list[Ticket]:
        return await self.repository.list_by_user(user_id)

    async def get_ticket(self, ticket_id: UUID, user_id: int) -> Ticket:
        ticket = await self.repository.get_owned(ticket_id, user_id)
        if ticket is None:
            raise TicketNotFoundError
        return ticket

    async def approve(self, ticket_id: UUID, user_id: int, payload: ApprovalRequest) -> Ticket:
        async with self.session.begin():
            ticket = await self.repository.get_owned(ticket_id, user_id)
            if ticket is None:
                raise TicketNotFoundError
            if ticket.status != "pending_approval":
                raise TicketStateError

            ticket.human_decision = payload.decision
            ticket.status = "executed" if payload.decision == "approved" else "rejected"
        return ticket

    async def _build_policy_refs(self, policy_nos: list[str]) -> list[dict]:
        policies = await self.policies.find_by_nos(policy_nos)
        # 按规则引擎给出的顺序输出，保证前端展示稳定
        index = {policy.policy_no: policy for policy in policies}
        return [
            {
                "policy_no": policy_no,
                "title": index[policy_no].title if policy_no in index else None,
                "id": index[policy_no].id if policy_no in index else None,
            }
            for policy_no in policy_nos
        ]
