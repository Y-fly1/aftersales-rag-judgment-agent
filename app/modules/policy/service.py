from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.policy.exceptions import PolicyNotFoundError
from app.modules.policy.models import Policy
from app.modules.policy.repository import PolicyRepository
from app.modules.policy.schemas import PolicyArticle, PolicyCategoryStat


class PolicyService:

    def __init__(self, session: AsyncSession):
        self.repository = PolicyRepository(session)

    async def list_policies(
        self,
        category: str | None = None,
        keyword: str | None = None,
    ) -> list[Policy]:
        return await self.repository.find_policies(
            category,
            keyword.strip() if keyword else None,
        )

    async def get_policy(self, policy_id: int) -> Policy:
        policy = await self.repository.get_by_id(policy_id)
        if policy is None:
            raise PolicyNotFoundError
        return policy

    async def list_categories(self) -> list[PolicyCategoryStat]:
        rows = await self.repository.count_by_category()
        return [PolicyCategoryStat(category=category, count=count) for category, count in rows]

    async def search_articles(self, policy_id: int, query: str, k: int = 5) -> list[PolicyArticle]:
        await self.get_policy(policy_id)

        from app.rag import retriever

        chunks = await retriever.retrieve(query, k, policy_id)
        return [
            PolicyArticle(section_path=chunk.section_path, content=chunk.content)
            for chunk in chunks
        ]
