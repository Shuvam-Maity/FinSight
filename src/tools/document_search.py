from langchain_core.tools import tool

from src import rag

_MAX_CHUNK_CHARS = 500


@tool
def search_documents(query: str) -> str:
    """Search the uploaded financial reports and documents for relevant information.
    Use this FIRST for any question that could be answered from the company reports
    (revenue, earnings, risks, segments, management commentary, etc.).
    Returns the matching passages with their source filename and page number.
    """
    docs = rag.retrieve(query)
    if not docs:
        return "No relevant information found in the uploaded documents."

    parts = []
    for i, d in enumerate(docs, 1):
        page = d.metadata.get("page")
        where = f"{d.metadata['filename']}, p.{page}" if page else d.metadata["filename"]
        content = d.page_content[:_MAX_CHUNK_CHARS]
        parts.append(f"[{i}] ({where})\n{content}")
    return "\n\n".join(parts)