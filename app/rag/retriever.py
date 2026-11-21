from langchain_core.vectorstores import VectorStore
from pymilvus import Function, FunctionType

from app.core.logging import get_logger
from app.infra.database import AsyncSessionFactory
from app.rag.models import PolicyChunk
from app.rag.repository import PolicyChunkRepository

logger = get_logger(__name__)


def create_reranker(query: str) -> Function:
    """Milvus reranker，使用阿里 gte-rerank-v2"""
    return Function(
        name="dashscope_semantic_ranker",
        input_field_names=["text"],
        function_type=FunctionType.RERANK,
        params={
            "reranker": "model",
            "provider": "ali",
            "model_name": "gte-rerank-v2",
            "queries": [query],
            "max_client_batch_size": 5,
        },
    )


class PolicyChunkRetriever:

    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        logger.info("RAG Retriever 初始化完成✅️")

    async def retrieve(self, query: str, k: int, policy_id: int) -> list[PolicyChunk]:
        # 1. 在指定政策内混合检索（dense + BM25），并用重排模型收敛结果
        child_chunks = await self.vector_store.asimilarity_search(
            query=query,
            k=k,
            fetch_k=10,
            expr=f"policy_id == {policy_id}",
            reranker=create_reranker(query),
        )

        # 2. 子块 → 父块，去重并保持重排顺序
        parent_ids = list(
            dict.fromkeys(
                chunk.metadata["parent_id"]
                for chunk in child_chunks
                if chunk.metadata.get("parent_id")
            )
        )
        if not parent_ids:
            return []

        async with AsyncSessionFactory() as session:
            repository = PolicyChunkRepository(session)
            chunks = await repository.search_chunks(parent_ids)

        order = {parent_id: index for index, parent_id in enumerate(parent_ids)}
        return sorted(chunks, key=lambda chunk: order.get(str(chunk.id), 999))
