from langchain_milvus import BM25BuiltInFunction, Milvus
from langchain_ollama import OllamaEmbeddings

from app.core.config import settings
from app.rag.pipeline import PolicyRAGPipeline
from app.rag.retriever import PolicyChunkRetriever

COLLECTION_NAME = "policy_collection"

_embeddings = OllamaEmbeddings(
    model="qwen3-embedding:0.6b",
    dimensions=1024,
)

_vector_store = Milvus(
    embedding_function=_embeddings,
    collection_name=COLLECTION_NAME,
    builtin_function=BM25BuiltInFunction(analyzer_params={"type": "chinese"}),
    vector_field=["dense", "sparse"],
    connection_args={"uri": settings.rag.milvus_url},
    auto_id=True,
)

pipeline = PolicyRAGPipeline(_vector_store)
retriever = PolicyChunkRetriever(_vector_store)


def close_rag() -> None:
    _vector_store.client.close()
    pipeline.close()
