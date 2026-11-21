from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.database import get_session
from app.modules.ticket.schemas import ApprovalRequest, TicketCreate, TicketResponse
from app.modules.ticket.service import TicketService

router = APIRouter(prefix="/api/v1/tickets", tags=["售后工单"])


def get_service(session: AsyncSession = Depends(get_session)) -> TicketService:
    return TicketService(session)


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    payload: TicketCreate,
    user_id: Annotated[int, Header(alias="x-user-id")],
    service: TicketService = Depends(get_service),
):
    """提交售后诉求，同步跑规则引擎判责；需人工时进入待审批状态"""
    ticket, _ = await service.create_and_judge(user_id, payload)
    return ticket


@router.get("", response_model=list[TicketResponse])
async def list_tickets(
    user_id: Annotated[int, Header(alias="x-user-id")],
    service: TicketService = Depends(get_service),
):
    return await service.list_tickets(user_id)


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: UUID,
    user_id: Annotated[int, Header(alias="x-user-id")],
    service: TicketService = Depends(get_service),
):
    return await service.get_ticket(ticket_id, user_id)


@router.patch("/{ticket_id}/approval", response_model=TicketResponse)
async def approve_ticket(
    ticket_id: UUID,
    payload: ApprovalRequest,
    user_id: Annotated[int, Header(alias="x-user-id")],
    service: TicketService = Depends(get_service),
):
    """人工审批：通过则执行，驳回则关闭"""
    return await service.approve(ticket_id, user_id, payload)
