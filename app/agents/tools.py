from langchain.tools import tool

from app.infra.database import AsyncSessionFactory
from app.modules.policy.service import PolicyService


@tool
async def search_policies(
    keywords: list[str],
    category: str | None = None,
    limit: int = 5,
) -> list[dict]:
    """检索售后政策。回答规则类问题前必须先调用本工具定位政策。

    Args:
        keywords: 关键词列表，如 ["七天无理由", "生鲜"]。
        category: 政策分类，可选 return(退货)/quality(质量)/logistics(物流)/fresh(生鲜)/large(大件)，不传则全库检索。
        limit: 最多返回条数，默认 5。
    """
    found: dict[int, object] = {}
    async with AsyncSessionFactory() as session:
        service = PolicyService(session)
        for keyword in dict.fromkeys(keywords):
            if not keyword.strip():
                continue
            policies = await service.list_policies(category, keyword.strip())
            for policy in policies:
                found.setdefault(policy.id, policy)
            if len(found) >= limit:
                break

    return [
        {
            "id": policy.id,
            "policy_no": policy.policy_no,
            "title": policy.title,
            "summary": policy.summary,
        }
        for policy in list(found.values())[:limit]
    ]


@tool
async def search_policy_article(query: str, policy_id: int) -> str:
    """查询指定政策的原文条款。回答"能退吗/多久内/谁承担运费"这类问题必须调用。

    Args:
        query: 要查询的问题，如"生鲜多久内可以申请售后"。
        policy_id: 政策 ID，来自 search_policies 返回结果。
    """
    from app.rag import retriever

    chunks = await retriever.retrieve(query, 5, policy_id)
    if not chunks:
        return "没有检索到相关条款，请勿编造，如实告知用户暂未找到依据。"
    return "\n\n".join(
        f"【{' > '.join(chunk.section_path)}】\n{chunk.content}" for chunk in chunks
    )
