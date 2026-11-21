from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.models import PolicyChunk


class PolicyChunkRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def delete_by_policy_id(self, policy_id: int) -> None:
        await self.session.execute(
            delete(PolicyChunk).where(PolicyChunk.policy_id == policy_id)
        )

    def add_all(self, chunks: list[PolicyChunk]) -> None:
        self.session.add_all(chunks)

    async def search_chunks(self, ids: list[str]) -> list[PolicyChunk]:
        if not ids:
            return []
        result = await self.session.execute(
            select(PolicyChunk).where(PolicyChunk.id.in_(ids))
        )
        return list(result.scalars().all())
