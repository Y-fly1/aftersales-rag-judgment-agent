"""把 data/raw/policies 下的政策 PDF 灌入 Milvus + policy_chunks

用法（在 agent-service 目录）：
    python -m scripts.ingest_policy
"""

import asyncio
import sys
from pathlib import Path

from langchain_milvus import BM25BuiltInFunction, Milvus
from langchain_ollama import OllamaEmbeddings

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings  # noqa: E402
from app.core.logging import get_logger  # noqa: E402
from app.infra.database import AsyncSessionFactory, close_database  # noqa: E402
from app.modules.policy.models import Policy  # noqa: E402
from app.rag.pipeline import PolicyRAGPipeline  # noqa: E402

logger = get_logger(__name__)
POLICY_ROOT = PROJECT_ROOT / "data" / "raw" / "policies"


def create_vector_store() -> Milvus:
    embeddings = OllamaEmbeddings(model="qwen3-embedding:0.6b", dimensions=1024)
    return Milvus(
        embedding_function=embeddings,
        collection_name="policy_collection",
        builtin_function=BM25BuiltInFunction(analyzer_params={"type": "chinese"}),
        vector_field=["dense", "sparse"],
        connection_args={"uri": settings.rag.milvus_url},
        auto_id=True,
    )


async def find_policies() -> list[Policy]:
    from sqlalchemy import select

    async with AsyncSessionFactory() as session:
        rows = await session.scalars(
            select(Policy).where(Policy.status == "in_force").order_by(Policy.id.asc())
        )
        return list(rows.all())


async def main() -> None:
    vector_store = create_vector_store()
    pipeline = PolicyRAGPipeline(vector_store)

    try:
        policies = await find_policies()
        logger.info("开始构建政策知识库", total=len(policies))

        for index, policy in enumerate(policies, start=1):
            if not (POLICY_ROOT / policy.doc_name).exists():
                logger.warning(
                    "原件缺失，跳过",
                    progress=f"{index}/{len(policies)}",
                    doc_name=policy.doc_name,
                )
                continue
            logger.info(
                "处理政策",
                progress=f"{index}/{len(policies)}",
                policy_no=policy.policy_no,
                title=policy.title,
            )
            await pipeline.ingest(policy)

        logger.info("政策知识库构建完成")
    finally:
        pipeline.close()
        vector_store.client.close()
        await close_database()


if __name__ == "__main__":
    asyncio.run(main())
