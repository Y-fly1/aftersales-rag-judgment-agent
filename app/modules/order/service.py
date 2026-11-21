from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.order.exceptions import OrderNotFoundError
from app.modules.order.models import Order
from app.modules.order.repository import OrderRepository


class OrderService:

    def __init__(self, session: AsyncSession):
        self.repository = OrderRepository(session)

    async def list_orders(self, user_id: int) -> list[Order]:
        return await self.repository.find_by_user(user_id)

    async def get_order(self, order_no: str, user_id: int) -> Order:
        order = await self.repository.get_by_order_no(order_no, user_id)
        if order is None:
            raise OrderNotFoundError
        return order
