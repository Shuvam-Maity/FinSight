# 📊 FinSight

**An agentic RAG assistant for financial documents.** Upload company reports (10-Ks, annual reports), ask questions in natural language, and get answers grounded in the documents — with the agent automatically reaching for live web search or a calculator when the documents alone aren't enough.

🔗 **Live demo:** [finsight-sm.streamlit.app](https://finsight-sm.streamlit.app/)

---

## What makes this different from a standard RAG app

Most RAG demos retrieve-then-answer in a fixed pipeline. FinSight is **agentic**: the LLM itself decides, per question, whether to search the uploaded documents, search the web, run a calculation, or some combination — then stops once it has a complete answer. It's also scoped to a single domain (finance/business) rather than acting as a general-purpose chatbot, and uses a real **MCP (Model Context Protocol)** connection for its web-search tool.

**Example:**
> *"What was Apple's gross margin in 2024, and is that competitive with other tech companies?"*

The agent pulls the exact figures from the uploaded 10-K, runs the margin calculation itself (never doing arithmetic "by eye"), and supplements with a live web search for industry comparison — citing both the document and the web sources it used.

## Features

- **Agentic tool use** — the LLM decides between document search, web search, and a calculator, and can chain multiple tools for one answer (LangGraph `create_react_agent`)
- **MCP web search** — connects to Tavily's hosted MCP server via `langchain-mcp-adapters`, not a hardcoded API wrapper
- **Table-aware PDF ingestion** — financial statements are detected with `pdfplumber`, converted to clean Markdown, and kept as single unsplit chunks (so a number never loses its row/column label during chunking)
- **Domain-scoped** — strictly declines non-finance questions rather than answering as a general chatbot
- **Role-based access** — a single admin account manages the shared document library; regular users can only ask questions
- **ChatGPT-style chat history** — per-user conversations with auto-generated titles, pinning, renaming, and deletion
- **Short- and long-term memory** — Redis caches the last 5 exchanges per chat (5-min TTL) for fast follow-up context; MongoDB holds the full permanent history
- **Source-grounded answers** — every answer cites the specific document passages or web results it used

## Architecture

```
┌─────────────┐
│  Streamlit  │  UI: login/signup, chat, admin document management
└──────┬──────┘
       │
┌──────▼──────────────────────────────────────┐
│          LangGraph ReAct Agent (Groq)         │
│  decides which tool(s) to call, if any        │
└───┬───────────────┬───────────────┬──────────┘
    │                │               │
┌───▼────────┐ ┌─────▼──────┐ ┌──────▼───────┐
│  Document   │ │ Web Search │ │  Calculator  │
│  Search     │ │ (Tavily,   │ │ (safe ast-   │
│  (Qdrant)   │ │  via MCP)  │ │  based eval) │
└─────────────┘ └────────────┘ └──────────────┘

MongoDB  — users, chat history (long-term)
Redis    — recent chat context (short-term, 5-min TTL)
Qdrant   — document embeddings (FastEmbed, BGE-small)
```

## Tech stack

| Layer | Choice |
|---|---|
| LLM | Groq (`openai/gpt-oss-120b`) |
| Agent framework | LangGraph (`create_react_agent`) |
| Web search | Tavily, via MCP (`langchain-mcp-adapters`) |
| Vector store | Qdrant Cloud |
| Embeddings | FastEmbed (`BAAI/bge-small-en-v1.5`), local, no GPU needed |
| Document parsing | `pypdf` + `pdfplumber` (table extraction), `docx2txt` |
| User & chat data | MongoDB Atlas |
| Short-term memory | Redis Cloud |
| Auth | bcrypt-hashed passwords |
| UI | Streamlit |
| Hosting | Streamlit Community Cloud |

## Project structure

```
finsight/
├── app.py                      # Streamlit UI + session orchestration
├── scripts/
│   ├── create_admin.py         # one-time script to seed the admin account
│   └── keepalive/
│       └── ping_qdrant.py      # keeps the free-tier Qdrant cluster active
├── src/
│   ├── core/                   # config, shared Groq client
│   ├── db/                     # MongoDB: users, chats
│   ├── auth/                   # signup/login, bcrypt
│   ├── chat/                   # chat title generation
│   ├── memory/                 # Redis short-term memory
│   ├── rag/                    # document loading, table-aware chunking,
│   │                           #   embeddings, Qdrant vector store
│   ├── tools/                  # the 3 agent tools (documents, web, calculator)
│   └── agent/                  # the ReAct agent + system prompt
└── .github/workflows/
    └── keepalive.yml           # daily cron job to prevent Qdrant auto-pause
```

## Running locally

**1. Clone and set up a virtual environment**
```bash
git clone https://github.com/Shuvam-Maity/FinSight.git
cd FinSight
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows PowerShell
pip install -r requirements.txt
```

**2. Set up accounts and get API keys/connection strings**
- [Groq](https://console.groq.com) — LLM
- [Qdrant Cloud](https://cloud.qdrant.io) — vector store (free tier)
- [MongoDB Atlas](https://cloud.mongodb.com) — users & chat history (free tier)
- [Redis Cloud](https://redis.io/try-free) — short-term memory (free tier)
- [Tavily](https://tavily.com) — web search (free tier)

**3. Configure `.env`**
```bash
cp .env.example .env
# fill in your real values
```

**4. Create the admin account**
```bash
python -m scripts.create_admin
```

**5. Run**
```bash
streamlit run app.py
```

## Known limitations

- Document retrieval uses a fixed relevance-score threshold rather than a learned reranker — tuned for the current document set, may need adjusting for very different content
- Single fixed admin account; no multi-admin support
- No persistent login — refreshing the browser logs you out (deliberate, simplicity over session cookies)
- Qdrant's free tier auto-pauses after 7 days of total inactivity; mitigated with a daily keep-alive job, but worth knowing about

## Roadmap ideas

- Re-ranking step before generation for stronger retrieval precision
- Multi-admin support with per-admin upload tracking
- Export chat history
- Support for more document formats (XLSX for raw financial data)

---

Built by [Shuvam Maity](https://github.com/Shuvam-Maity) — [LinkedIn](https://www.linkedin.com/in/shuvam-maity/)