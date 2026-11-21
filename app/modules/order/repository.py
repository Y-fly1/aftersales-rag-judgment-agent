from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.order.models import Order


class OrderRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_user(self, user_id: int, limit: int = 20) -> list[Order]:
        rows = await self.session.scalars(
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .limit(limit)
        )
        return list(rows.all())

    async def get_by_order_no(self, order_no: str, user_id: int) -> Order | None:
        return await self.session.scalar(
            select(Order).where(
                Order.order_no == order_no,
                Order.user_id == user_id,
            )
        )

    async def get_by_order_no_unscoped(self, order_no: str) -> Order | None:
        """供 Agent 工具使用：先取订单再校验归属，便于给出更准确的提示"""
        return await self.session.scalar(
            select(Order).where(Order.order_no == order_no)
        )
