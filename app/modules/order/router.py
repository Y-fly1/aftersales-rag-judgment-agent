from typing import Annotated

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.database import get_session
from app.modules.order.schemas import OrderResponse
from app.modules.order.service import OrderService

router = APIRouter(prefix="/api/v1/orders", tags=["订单"])


def get_service(session: AsyncSession = Depends(get_session)) -> OrderService:
    return OrderService(session)


@router.get("", response_model=list[OrderResponse])
async def list_orders(
    user_id: Annotated[int, Header(alias="x-user-id")],
    service: OrderService = Depends(get_service),
):
    return await service.list_orders(user_id)


@router.get("/{order_no}", response_model=OrderResponse)
async def get_order(
    order_no: str,
    user_id: Annotated[int, Header(alias="x-user-id")],
    service: OrderService = Depends(get_service),
):
    return await service.get_order(order_no, user_id)
