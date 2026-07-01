# miniAI — Full-Stack Next.js Documentation Assistant

A production-style **Next.js documentation assistant**: chat with an LLM that answers Next.js questions grounded in the **official Next.js docs**, can also reason over **your own uploaded files**, and pulls in **live web search** when currency matters — all in one streaming conversation. Built as a full application, not a notebook: real auth, per-conversation memory, direct-to-S3 uploads, a content-aware document ingestion pipeline, and a routed multi-model **LangGraph** agent.

> **Monorepo layout**
> - [`AI-Assistant-Backend/`](./AI-Assistant-Backend) — FastAPI + LangGraph agent, RAG pipeline, auth, storage
> - [`AI-Assistant-Frontend/`](./AI-Assistant-Frontend) — Next.js 16 (App Router) + React 19 streaming chat UI

---

## Why this project is interesting

Most "RAG demos" stop at *load a PDF → embed → answer*. This one is engineered like a real product:

- **Grounded in the real Next.js docs.** The official Next.js documentation is ingested as a curated knowledge base; any Next.js question is answered from those docs (with citations) rather than from the model's memory — so answers stay accurate and version-aligned.
- **An LLM router, not a single model.** A query-analyzer node classifies each turn (intent + category) and fans out to the right retrieval sources, then a synthesizer answers with the model best suited to the task — cheap-and-fast for general chat, stronger models for math/code, a vision model for images.
- **Multi-source retrieval in one answer.** A single question can pull from the Next.js docs **and** the user's own uploaded files **and** the web simultaneously (e.g. "does my `page.tsx` follow the App Router conventions?"), with every claim cited by origin.
- **A real ingestion pipeline.** Documents are routed by *content*, not just file extension — a scanned or image-heavy PDF is detected and sent through a vision LLM, while a clean digital PDF takes a fast text-extraction path.
- **Correct streaming, auth, and multi-tenancy.** Server-Sent Events end to end, httpOnly-cookie JWT auth, and strict per-user / per-chat isolation across Postgres, S3, and the vector store.

---

## Architecture at a glance

```
┌──────────────────────────┐         SSE + REST          ┌───────────────────────────────────────┐
│   Next.js 16 Frontend    │  ───────────────────────▶   │            FastAPI Backend            │
│                          │                             │                                       │
│  • App Router / React 19 │   POST /api/chat/stream     │   api/  (web layer)                   │
│  • Streaming chat UI     │   (text/event-stream)       │     auth · chats · storage · ingest   │
│  • Direct-to-S3 uploads  │                             │   app/  (agent layer)                 │
│  • httpOnly cookie auth  │   PUT (presigned) ─────────▶│     LangGraph agent + RAG pipeline    │
└──────────────────────────┘        direct to S3         └───────────────────────────────────────┘
                                                              │          │           │         │
                                                    ┌─────────┘   ┌──────┘    ┌───────┘   ┌─────┘
                                                    ▼             ▼           ▼           ▼
                                              Postgres       Pinecone      S3 bucket   Tavily / Cohere
                                            (Supabase)     (vectors +     (Supabase)   (web search +
                                          chats + memory   1 tenant ns)    files/md     rerank)
```

**The LangGraph agent flow:**

```
START
  → query_analyzer_node        # structured output → intent[] + rewritten_query + category
  → route_after_analysis       # fan-out by intent
      ├─ direct        → synthesizer
      ├─ user_docs     → Pinecone (filter: this chat's uploads)      ─┐
      ├─ nextjs_docs   → Pinecone (filter: Next.js docs corpus)      ─┤
      └─ web_search    → Tavily (MCP)                                ─┤
  → synthesizer_agent_node     # model routed per-turn; STREAMS to client; cites sources
  → context_management_node    # summarize / truncate as history grows
  → END
```

Intents can run **in parallel** (e.g. check *your* uploaded component against the *Next.js docs* in one turn). Each retrieval branch writes its own state channel and the synthesizer merges them, citing each by origin (`[Your upload · …]` vs `[Next.js Docs · topic · …]`).

---

## Key features

| Area | What it does |
| ---- | ------------ |
| **Next.js docs Q&A** | Answers Next.js questions from a curated knowledge base built from the official docs — the analyzer routes any Next.js query to the docs corpus and the synthesizer cites the pages it used. |
| **Streaming chat** | Token-by-token replies over Server-Sent Events; the SSE frame contract is mirrored on the client parser. |
| **Per-conversation memory** | LangGraph `AsyncPostgresSaver` checkpointer keyed on `chat_id`, so each thread remembers its own context. |
| **Retrieval-augmented generation** | Documents chunked and embedded into Pinecone; retrieval returns a broad candidate pool, then **Cohere `rerank-v3.5`** keeps only chunks above a relevance threshold (adaptive top-k, not fixed). |
| **Content-aware ingestion** | PDFs are profiled (chars/page, images/page, tables, columns) to choose a fast text path (`pymupdf4llm`) or a **Gemini vision** path for scanned/complex docs; Office docs via `markitdown` (+ LibreOffice→vision for image-first files). |
| **Query-aware attachments** | Attach a doc and ask about *any* part of it — large files are chunked and reranked against the question so the relevant excerpts (not just page 1) reach the model on the same turn; follow-ups retrieve the whole doc via RAG. |
| **Multi-model routing** | Per-turn model selection: vision model for images, stronger models for math/code, fast model for general chat — with provider fallbacks that fire only on errors. |
| **Direct-to-S3 uploads** | Presigned PUT URLs — bytes never pass through the backend. Files are scoped to `{user_id}/{chat_id}/`. |
| **Web search** | Live results via **Tavily** through the Model Context Protocol (MCP). |
| **Auth & multi-tenancy** | JWT in an httpOnly cookie, bcrypt hashing, and application-level ownership gates on every chat/file/vector. |
| **Clean deletion** | Deleting a chat tears down its footprint across all four stores — Postgres rows, S3 prefix, Pinecone vectors, and checkpointer thread. |
| **Retrieval evaluation** | A standalone harness measuring Keyword-match / Source-match / MRR, with a toggle to A/B the reranker's lift. |

---

## Tech stack

**Backend**
- **FastAPI** (ASGI, Uvicorn) — REST + SSE
- **LangGraph** `StateGraph` with a Postgres checkpointer
- **LangChain** across multiple providers: OpenAI (GPT-5 family), DeepSeek, Google Gemini 2.5, Groq
- **Pinecone** vector store (single tenant namespace, per-chat metadata isolation) with `text-embedding-3-small`
- **Cohere** `rerank-v3.5` for retrieval re-ranking
- **Tavily** web search via **MCP**
- **Supabase** — Postgres (async SQLModel / `asyncpg`) + S3-compatible object storage (`boto3` presigned URLs)
- Document conversion: `pymupdf4llm`, `markitdown`, Gemini vision, headless LibreOffice
- **LangSmith** tracing; `pydantic-settings` config

**Frontend**
- **Next.js 16** (App Router, Turbopack) + **React 19**
- **TypeScript 5** (strict) — no `any`, no `@ts-ignore`
- **Tailwind CSS v4** with CSS-custom-property theming (class-based dark mode, hydration-safe via `useSyncExternalStore`)
- Hand-rolled UI (no component kit); `react-markdown` + `remark-gfm` for assistant replies
- Typed API client layer; SSE stream reader

---

## How it works — a few engineering highlights

**One vector namespace, isolated by metadata.** Instead of a namespace per chat (which doesn't scale on serverless Pinecone), every vector lives in a single tenant namespace and is separated by metadata: per-chat uploads are tagged `source="user_upload"` + `chat_id`; the shared Next.js docs KB is tagged `source="company"` + `topic="nextjs"`. Vector IDs are prefixed (`{chat_id}#…` for uploads, `nextjs#{topic}#…` for the docs) so a subset can be deleted without a metadata-filter delete (which serverless doesn't support).

**Adaptive retrieval with a reranker.** Retrievers pull a broad similarity pool (recall), then a Cohere cross-encoder scores and keeps *every* chunk above a relevance threshold — so a sharp query surfaces several chunks, a vague one few, an off-topic one none. Re-ranking is best-effort and falls back to similarity order if unavailable, so retrieval never hard-fails.

**Content-aware document routing.** A scanned PDF and a digital PDF are the same MIME type but need completely different handling. The classifier profiles the actual bytes to decide between a fast text path and a vision-LLM path, with graceful fallbacks when optional tooling (e.g. LibreOffice) is missing.

**Query-aware attachments (not just the first pages).** When a document is attached, small files go into the synthesizer's prompt whole, but a large file is chunked and **Cohere-reranked against the current question** — the most-relevant excerpts are packed to a token budget (in document order), so "what does section 12 say?" works on the *same* turn, before async indexing finishes, instead of the model only seeing the opening pages. Huge docs are first narrowed by a cheap lexical pre-filter to stay under the reranker's per-call limit while keeping whole-document coverage. Two levers make retrieval reliable on follow-ups: attaching a doc **forces** the `user_docs` retrieval branch, and a `has_user_docs` flag **nudges** the analyzer to route later content questions to the doc (it otherwise only sees clean text and can't tell a file was uploaded earlier). The attachment context is set fresh per turn, so it never replays or balloons. Images are inlined to a vision model as base64.

**Streaming that stays in sync.** Only the synthesizer node's output streams to the client; the SSE frame shapes (`chat_id` / `delta` / `[DONE]` / `error`) are defined once and parsed by a matching client reader — a deliberately small, tested contract.

---

## Getting started

> The project reads secrets from `.env` files (never committed). You'll need credentials for OpenAI, Google Gemini, DeepSeek, Groq, Cohere, Pinecone, Tavily (MCP), and Supabase (Postgres + S3).

### Backend

```bash
cd AI-Assistant-Backend
# create a .env with the required keys (see AI-Assistant-Backend/CLAUDE.md → Config)
python main.py            # uvicorn, reload, http://localhost:8000
```

Interactive API docs: `http://localhost:8000/docs`.

Load the Next.js documentation knowledge base (grab the docs folder from [`vercel/next.js/tree/canary/docs`](https://github.com/vercel/next.js/tree/canary/docs)):

```bash
python -m src.app.rag_pipeline.data_ingestion.offline_batch_ingestion --dir path/to/next.js/docs --topic nextjs
```

Optionally check retrieval quality against the bundled Next.js eval set:

```bash
python -m src.app.rag_pipeline.evaluation.retrieval_eval --topic nextjs
```

### Frontend

```bash
cd AI-Assistant-Frontend
pnpm install
# .env.local → NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
pnpm dev                  # http://localhost:3000
```

> **Local dev auth note:** the session cookie is `SameSite=Lax`, so the frontend and backend must be same-site. Run the backend with `COOKIE_SECURE=false` over plain HTTP and point the frontend at `http://localhost:8000`, or auth will appear to "log in then instantly log out."

---

## Repository structure

```
AI-Assistant-App/
├── AI-Assistant-Backend/          # FastAPI + LangGraph
│   ├── app.py / main.py           # ASGI app + entry point
│   ├── config.py                  # pydantic-settings
│   └── src/
│       ├── api/                   # web layer: routes, auth, DB models, S3, ingestion
│       └── app/                   # agent layer: graph, nodes, models, RAG pipeline, MCP
│           └── rag_pipeline/      # converters, chunking, vector store, reranker, eval
└── AI-Assistant-Frontend/         # Next.js 16 App Router
    ├── app/                       # routes: (auth) + (app) groups
    ├── components/                # chat, shell, theme, hand-rolled ui
    └── lib/api/                   # typed client layer (REST + SSE)
```

Each package has a detailed `CLAUDE.md` documenting its internals; the RAG subsystem has its own guide under `src/app/rag_pipeline/`.

---

## Notes

- **No test suite yet** and **no automated DB migrations** (tables are created on startup; schema changes are manual) — deliberate scoping choices for a portfolio build, called out for honesty.
- Multi-tenancy is enforced at the **application layer**; bucket policies / RLS would be the next hardening step for defense-in-depth.

---

*Built by Abhyuday Gupta as a demonstration of production-oriented GenAI engineering: agentic orchestration, retrieval quality, and full-stack delivery.*
