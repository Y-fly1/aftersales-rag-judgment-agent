from pathlib import Path
from typing import Any
from uuid import uuid4

from langchain.chat_models import init_chat_model
from langchain_core.vectorstores import VectorStore
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)
from mineru import ExtractResult, MinerU

from app.core.config import APP_ROOT, settings
from app.infra.database import AsyncSessionFactory
from app.modules.policy.models import Policy
from app.rag.models import PolicyChunk
from app.rag.repository import PolicyChunkRepository

MARKDOWN_OPTIMIZATION_PROMPT = """
下面这份 Markdown 是从售后政策 / 平台规则 PDF 解析得来，PDF 里的小节以表格形式存在，解析后出现错乱。
请把它整理成格式正确的 Markdown，重点是条款编号要正确。
- 标题从 1 级开始逐层增加，目录和文档名不计入标题等级。
- 「一、」「（一）」「1.」这类条款编号必须保留在正文，不要合并成一段。
- 不要包含正文开始之前的部分。
- 只输出 Markdown 正文，不要解释、不要代码围栏。
- 严禁改写、简化、润色任何规则原文。
""".strip()


class PolicyRAGPipeline:

    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.mineru = MinerU(settings.rag.mineru_token)
        self.llm = init_chat_model(
            settings.llm.chat_model,
            api_key=settings.llm.api_key,
            extra_body={"thinking": {"type": "disabled"}},
            max_tokens=8000,
        )
        self.markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "h1"),
                ("##", "h2"),
                ("###", "h3"),
                ("####", "h4"),
            ],
            strip_headers=False,
        )
        self.child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", "。", "；", ";", "，", ","],
            keep_separator="end",
        )

    async def ingest(self, policy: Policy) -> None:
        doc_name, result = await self._load_document(policy)
        markdown = await self._document_optimize(result)
        child_chunks, parent_chunks = await self._split_document(doc_name, markdown, policy)
        await self._save_child_chunks(child_chunks, policy)
        await self._save_parent_chunks(parent_chunks, policy)

    async def _save_parent_chunks(self, chunks: list[PolicyChunk], policy: Policy) -> None:
        async with AsyncSessionFactory() as session:
            async with session.begin():
                repository = PolicyChunkRepository(session)
                await repository.delete_by_policy_id(policy.id)
                repository.add_all(chunks)

    async def _save_child_chunks(self, chunks: list[Any], policy: Policy) -> None:
        self.vector_store.delete(expr=f"policy_id == {policy.id}")
        if chunks:
            self.vector_store.add_documents(chunks)

    async def _split_document(
        self,
        doc_name: str,
        markdown: str,
        policy: Policy,
    ) -> tuple[list[Any], list[PolicyChunk]]:
        parent_chunks: list[PolicyChunk] = []
        child_chunks: list[Any] = []

        for parent_doc in self.markdown_splitter.split_text(markdown):
            section_path = list(parent_doc.metadata.values())
            parent_chunk = PolicyChunk(
                id=uuid4(),
                policy_id=policy.id,
                doc_name=doc_name,
                content=parent_doc.page_content,
                section_path=section_path,
            )
            parent_chunks.append(parent_chunk)

            parent_doc.metadata = {
                "parent_id": str(parent_chunk.id),
                "policy_id": policy.id,
            }
            children = self.child_splitter.split_documents([parent_doc])
            header = "\n".join(section_path) + "\n"
            for child in children:
                child.page_content = header + child.page_content
            child_chunks.extend(children)

        return child_chunks, parent_chunks

    async def _document_optimize(self, result: ExtractResult) -> str:
        response = self.llm.invoke(
            [
                {"role": "system", "content": MARKDOWN_OPTIMIZATION_PROMPT},
                {"role": "user", "content": result.markdown},
            ]
        )
        return response.content

    async def _load_document(self, policy: Policy) -> tuple[str, ExtractResult]:
        doc_name = policy.doc_name
        path = Path(APP_ROOT / "data" / "raw" / "policies" / doc_name)
        if not path.exists():
            raise FileNotFoundError(f"政策原件缺失: {path}")
        return doc_name, self.mineru.extract(str(path))

    def close(self) -> None:
        self.mineru.close()
