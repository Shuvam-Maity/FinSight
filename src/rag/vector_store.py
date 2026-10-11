from functools import lru_cache

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models

from src.core.config import Settings, get_settings


# ---------- embeddings ----------

class FastEmbedEmbeddings(Embeddings):
    """Thin LangChain wrapper around fastembed (local ONNX, no PyTorch)."""

    def __init__(self, model_name: str, cache_dir: str | None = None):
        from fastembed import TextEmbedding

        self._model = TextEmbedding(model_name=model_name, cache_dir=cache_dir)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [v.tolist() for v in self._model.passage_embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        return next(iter(self._model.query_embed(text))).tolist()


@lru_cache
def get_embeddings() -> FastEmbedEmbeddings:
    s = get_settings()
    return FastEmbedEmbeddings(s.embed_model, cache_dir=str(s.embed_cache_dir))


# ---------- Qdrant client + collection ----------

def _ensure_collection(client: QdrantClient, s: Settings) -> None:
    if client.collection_exists(s.collection_name):
        return
    client.create_collection(
        collection_name=s.collection_name,
        vectors_config=models.VectorParams(size=s.embed_dim, distance=models.Distance.COSINE),
    )
    client.create_payload_index(
        collection_name=s.collection_name,
        field_name="metadata.doc_id",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )


@lru_cache
def get_client() -> QdrantClient:
    s = get_settings()
    client = QdrantClient(url=s.qdrant_url, api_key=s.qdrant_api_key)
    _ensure_collection(client, s)
    return client


@lru_cache
def get_vector_store() -> QdrantVectorStore:
    return QdrantVectorStore(
        client=get_client(),
        collection_name=get_settings().collection_name,
        embedding=get_embeddings(),
    )


# ---------- writes and search: shared across all users, scoped only by doc_id ----------

def add_chunks(chunks: list[Document], doc_id: str) -> int:
    for chunk in chunks:
        chunk.metadata = {**chunk.metadata, "doc_id": doc_id}
    get_vector_store().add_documents(chunks)
    return len(chunks)


def search(query: str, k: int | None = None) -> list[Document]:
    """Unfiltered across all documents, but only chunks above the relevance threshold."""
    s = get_settings()
    results = get_vector_store().similarity_search_with_score(query, k=k or s.top_k)
    return [doc for doc, score in results if score >= s.score_threshold]


def delete_by_doc_id(doc_id: str) -> None:
    get_client().delete(
        collection_name=get_settings().collection_name,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[models.FieldCondition(key="metadata.doc_id", match=models.MatchValue(value=doc_id))]
            )
        ),
    )