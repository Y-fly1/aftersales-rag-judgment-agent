from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ticket.models import Ticket


class TicketRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    def add(self, ticket: Ticket) -> Ticket:
        self.session.add(ticket)
        return ticket

    async def get_owned(self, ticket_id: UUID, user_id: int) -> Ticket | None:
        return await self.session.scalar(
            select(Ticket).where(
                Ticket.id == ticket_id,
                Ticket.user_id == user_id,
            )
        )

    async def find_by_order(self, order_no: str, user_id: int) -> list[Ticket]:
        rows = await self.session.scalars(
            select(Ticket)
            .where(Ticket.order_no == order_no, Ticket.user_id == user_id)
            .order_by(Ticket.created_at.desc())
        )
        return list(rows.all())

    async def list_by_user(self, user_id: int, limit: int = 50) -> list[Ticket]:
        rows = await self.session.scalars(
            select(Ticket)
            .where(Ticket.user_id == user_id)
            .order_by(Ticket.created_at.desc())
            .limit(limit)
        )
        return list(rows.all())
