from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.core.config import get_settings


def split_documents(docs: list[Document]) -> list[Document]:
    """Split regular text into overlapping chunks. Table chunks (chunk_type="table")
    are kept whole, since splitting a table mid-row destroys its meaning."""
    s = get_settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=s.chunk_size,
        chunk_overlap=s.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: list[Document] = []
    for doc in docs:
        if doc.metadata.get("chunk_type") == "table":
            chunks.append(doc)
        else:
            chunks.extend(splitter.split_documents([doc]))

    chunks = [c for c in chunks if c.page_content.strip()]
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = i
    return chunks