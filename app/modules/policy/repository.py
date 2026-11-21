from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.policy.models import Policy


class PolicyRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_policies(
        self,
        category: str | None = None,
        keyword: str | None = None,
    ) -> list[Policy]:
        conditions = [Policy.status == "in_force"]
        if category:
            conditions.append(Policy.category == category)
        if keyword:
            pattern = f"%{keyword}%"
            conditions.append(
                or_(
                    Policy.title.ilike(pattern),
                    Policy.summary.ilike(pattern),
                    Policy.policy_no.ilike(pattern),
                )
            )

        rows = await self.session.scalars(
            select(Policy).where(*conditions).order_by(Policy.id.asc())
        )
        return list(rows.all())

    async def get_by_id(self, policy_id: int) -> Policy | None:
        return await self.session.get(Policy, policy_id)

    async def find_by_nos(self, policy_nos: list[str]) -> list[Policy]:
        if not policy_nos:
            return []
        rows = await self.session.scalars(
            select(Policy).where(Policy.policy_no.in_(policy_nos))
        )
        return list(rows.all())

    async def count_by_category(self) -> list[tuple[str, int]]:
        rows = await self.session.execute(
            select(Policy.category, func.count())
            .where(Policy.status == "in_force")
            .group_by(Policy.category)
            .order_by(func.count().desc())
        )
        return [(category, count) for category, count in rows.all()]
