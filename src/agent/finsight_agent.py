from langgraph.prebuilt import create_react_agent

from src.core.llm import get_llm
from src.tools.calculator import calculate
from src.tools.document_search import search_documents
from src.tools.web_search import get_web_search_tools
import re

_CITATION_PATTERN = re.compile(r"【[^】]*】")

SYSTEM_PROMPT = """You are FinSight, a financial document assistant.

Rules:
1. Always check uploaded documents (search_documents) first for anything about a
   company's figures, statements, or commentary.
2. If documents lack the answer, or the question needs current/external info
   (prices, news, ongoing status), use web search.
3. Use the calculate tool for any derived number (growth, margin, ratio, %
   change). Never do arithmetic yourself.
4. Use multiple tools only if genuinely needed. Stop once the answer is
   complete.
5. Cite sources: [1], [2] for documents; note when info is from the web.
6. If no source has the answer, say so. Never fabricate figures.
7. ONLY answer finance/business/company/market/economy questions. Hard rule,
   no exceptions — not for poems, jokes, trivia, coding, or any other
   non-financial request. If off-topic, respond ONLY with: "I'm a financial
   assistant and can only help with finance, business, and company-report
   questions." Do not generate any of the requested content.
"""


async def build_agent():
    web_tools = await get_web_search_tools()
    tools = [search_documents, calculate, *web_tools]
    return create_react_agent(model=get_llm(), tools=tools, prompt=SYSTEM_PROMPT)

def clean_citations(text: str) -> str:
    """Strip the model's internal tool-citation markup (e.g. 【1†L1-L4】)."""
    return _CITATION_PATTERN.sub("", text).strip()