from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.database import get_session
from app.modules.policy.schemas import (
    PolicyArticle,
    PolicyCategoryStat,
    PolicyResponse,
)
from app.modules.policy.service import PolicyService

router = APIRouter(prefix="/api/v1/policies", tags=["售后政策"])


def get_service(session: AsyncSession = Depends(get_session)) -> PolicyService:
    return PolicyService(session)


@router.get("", response_model=list[PolicyResponse])
async def list_policies(
    category: str | None = Query(
        default=None,
        pattern="^(return|quality|logistics|fresh|large|general)$",
    ),
    q: str | None = Query(default=None, max_length=100),
    service: PolicyService = Depends(get_service),
):
    return await service.list_policies(category, q)


@router.get("/categories", response_model=list[PolicyCategoryStat])
async def list_categories(service: PolicyService = Depends(get_service)):
    return await service.list_categories()


@router.get("/{policy_id}", response_model=PolicyResponse)
async def get_policy(
    policy_id: int,
    service: PolicyService = Depends(get_service),
):
    return await service.get_policy(policy_id)


@router.get("/{policy_id}/articles", response_model=list[PolicyArticle])
async def search_articles(
    policy_id: int,
    q: str = Query(min_length=1, max_length=200),
    k: int = Query(default=5, ge=1, le=20),
    service: PolicyService = Depends(get_service),
):
    return await service.search_articles(policy_id, q, k)
