# RAG with LangChain — EmotionAI Study Guide

> Personal reference written while planning and building the M3 RAG pipeline for EmotionAI.
> All examples use real file paths and real code patterns from this project.

---

## What is it and why do we use it here

### The hallucination problem

A raw LLM call is stateless. Every time you send a message to GPT-4, it knows nothing
about your user. It cannot say "last Tuesday you felt anxious before your work meeting"
because it has no access to that information. What it _can_ do — and will do if you let it —
is generate a plausible-sounding but fabricated response. This is called hallucination:
the model confidently invents facts it has no basis for.

For a general chatbot, hallucination is annoying. For a mental health app, it is dangerous.
A therapist who misremembers your history or invents patterns you never showed is not just
unhelpful — they are actively harmful.

### What RAG does

RAG — Retrieval-Augmented Generation — is the standard solution. Before calling the LLM,
you _retrieve_ real data relevant to the current query, then _augment_ the prompt with that
data, so the LLM _generates_ a response grounded in verified facts.

```
Without RAG:
  User: "I've been feeling overwhelmed a lot lately"
  LLM:  "Many people feel overwhelmed from time to time..." (generic, invented)

With RAG:
  1. Retrieve: user's last 7 days → anxiety x4, work stress x3, poor sleep x2
  2. Augment:  inject those records into the system prompt
  3. Generate: "I can see you've logged anxiety four times this week, often linked to
               work stress. That's a clear pattern worth exploring together."
```

The second response is therapeutic because it is true. The model is not guessing — it is
reasoning over real data you provided.

### Why EmotionAI specifically needs it

EmotionAI stores rich per-user history: emotional records with intensity scores, breathing
session outcomes, conversation history, and MBTI/behavioral profiles. Without RAG, none of
this data reaches the LLM. The therapeutic agent responds as if meeting the user for the
first time on every message.

Milestone 3 (see `.planning/ROADMAP.md` §M3) fixes this by building a semantic memory
system that retrieves the most relevant pieces of that history and injects them into the
LangChain agent's context window before each GPT-4 call.

---

## How it works conceptually

### The three-step pipeline

```
User sends message
       │
       ▼
┌─────────────────────────────────────────────────────┐
│  1. RETRIEVE                                        │
│                                                     │
│  "What does this user know that is relevant         │
│   to their current message?"                        │
│                                                     │
│  Query: embed(user_message) → cosine similarity     │
│  Search: pgvector finds top-k matching records      │
│  Result: 3-5 chunks of user's emotional history     │
└────────────────────────┬────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│  2. AUGMENT                                         │
│                                                     │
│  Build the system prompt:                           │
│  [base therapeutic instructions]                    │
│  + [user profile: MBTI, goals]                      │
│  + [retrieved history: relevant past records]       │
│  + [recent conversation turns: last 6 messages]     │
└────────────────────────┬────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│  3. GENERATE                                        │
│                                                     │
│  Send augmented prompt to GPT-4                     │
│  Parse JSON response                                │
│  Return TherapyResponse with crisis_detected flag   │
└─────────────────────────────────────────────────────┘
```

### Embeddings — how retrieval actually works

An embedding is a list of floating-point numbers (a vector) that represents the _meaning_
of a piece of text. Texts with similar meanings produce vectors that are close together in
high-dimensional space. This is what makes semantic search work.

```
"I feel really anxious about my job interview tomorrow"
  → [0.021, -0.184, 0.093, ... 1536 numbers]  ← OpenAI text-embedding-3-small

"nervous about work presentation next week"
  → [0.018, -0.179, 0.089, ... 1536 numbers]  ← similar vector, similar meaning

"my dog enjoys playing fetch"
  → [0.412,  0.234, -0.321, ... 1536 numbers] ← very different vector, different meaning
```

The distance between vectors is measured with **cosine similarity** — a score from 0
(unrelated) to 1 (identical meaning). pgvector stores these vectors in PostgreSQL and can
find the k nearest neighbours using an efficient HNSW index.

### Context window management

Every LLM has a context window limit — the maximum number of tokens it can process in one
call. GPT-4 supports 8,192 tokens (or 128k for GPT-4-turbo). Your augmented prompt must
fit within this limit.

```
Context window budget (example, GPT-4 8k):
  system prompt base:        ~300 tokens
  user profile:              ~100 tokens
  retrieved history (top-3): ~600 tokens   ← RAG chunks
  conversation history (6):  ~400 tokens
  user message:              ~50 tokens
  response buffer:           ~500 tokens
  ──────────────────────────────────────
  total:                   ~1,950 tokens   ← comfortably fits
```

If you retrieve too many chunks, or your system prompt is too long, you will hit the limit
and the API call will fail — or worse, the model will truncate your context silently and
"forget" important information.

### Explaining it to a junior developer

Think of it like a doctor preparing for a patient appointment. Before seeing the patient
the doctor reads their notes: past diagnoses, medication history, recent test results. They
do not memorise all patients at once — they _retrieve_ this one patient's relevant file.
Then they _augment_ their medical knowledge with that file. Then they _generate_ a response
tailored to this specific person.

RAG is that preparation step. The LLM is the doctor. Your database is the filing cabinet.

---

## Key patterns used in this project

### What the current implementation does (pre-RAG)

`_build_agent_context` in
`src/infrastructure/services/langchain_agent_service.py` (line 138) currently assembles
context through four database queries:

```python
# src/infrastructure/services/langchain_agent_service.py — _build_agent_context

# 1. Recent conversation messages (last 10, chronological)
recent_messages = await self.conversation_repository.get_recent_context(
    user_id, agent_type, message_count=10
)

# 2. User profile (MBTI, age, therapy goals, preferences)
user_profile = await self._get_user_profile(user_id)

# 3. Emotional state of the current message (a secondary LLM call — GPT-4o-mini)
emotional_analysis = await self.llm_service.analyze_emotional_state(current_message)

# 4. Recent emotional records — last 7 days, capped at 10
emotional_records = await self._get_recent_emotional_records(user_id)
```

This context is assembled into an `AgentContext` dataclass
(`src/domain/chat/entities.py` line 39) and passed to `OpenAILLMService.generate_therapy_response`.

The system prompt is built in
`src/infrastructure/services/openai_llm_service.py` `_create_therapy_system_prompt` (line 95).
It inlines the user profile and emotional state as JSON strings:

```python
# src/infrastructure/services/openai_llm_service.py — _create_therapy_system_prompt

system_prompt = f"""You are a professional {context.agent_type} AI assistant...
User Profile: {json.dumps(context.user_profile, default=str)}
Current Emotional State: {context.emotional_state or "unknown"}
Session Duration: {context.session_duration or 0} minutes
...
"""
```

Conversation history is appended as separate messages, limited to 6 turns:

```python
# _build_conversation_history: last 6 messages only
for msg in messages[-6:]:
    role = "assistant" if msg.message_type == "assistant" else "user"
    history.append({"role": role, "content": msg.content})
```

**The limitation:** retrieval is purely time-based (last 7 days, last 10 messages). There
is no semantic matching. A user who mentioned work anxiety three weeks ago gets no benefit
from that history even if today's message is directly about work anxiety.

The `ISimilaritySearchService` interface exists in
`src/application/services/similarity_search_service.py` but its only concrete
implementation is `MockSimilaritySearchService`
(`src/infrastructure/services/mock_similarity_search_service.py`) which returns empty
lists for every query.

### What the M3 RAG upgrade adds

The plan in `.planning/ROADMAP.md` (Milestone 3, slice 3.2) introduces:

**A new `rag_context_builder.py` use case** at
`src/application/chat/use_cases/rag_context_builder.py` that replaces time-based retrieval
with semantic retrieval:

```python
# Planned: src/application/chat/use_cases/rag_context_builder.py

async def build_rag_context(
    self,
    user_id: UUID,
    query: str,
    top_k: int = 5
) -> List[RetrievedChunk]:
    # 1. Embed the user's current message
    query_embedding = await self.embedding_service.embed(query)

    # 2. Search pgvector for semantically similar chunks
    chunks = await self.similarity_search_service.find_similar_content(
        user_id=user_id,
        query_vector=query_embedding,
        limit=top_k
    )

    return chunks
```

**A `vector_embeddings` table** (new Alembic migration) with schema:

```python
# Planned addition to src/infrastructure/database/models.py

class VectorEmbeddingModel(Base):
    __tablename__ = "vector_embeddings"
    id:             UUID primary key
    user_id:        UUID (FK users.id)
    source_type:    str  ("record" | "chat" | "profile")
    source_id:      UUID
    embedding:      Vector(1536)   # pgvector column
    content_preview: str           # human-readable summary
    created_at:     datetime
```

**Embeddings generated asynchronously** via a Celery task (M2 infrastructure, already in
place at `src/infrastructure/tasks/`) triggered after a new emotional record or chat
message is saved.

**The retrieval chain design** for EmotionAI specifically:

```
When user sends "I feel overwhelmed by work again":

  1. Embed query → vector Q
  2. pgvector: SELECT ... ORDER BY embedding <-> Q LIMIT 5
     Returns:
       - emotional_record: "anxious, work, 8/10" (2 weeks ago)
       - emotional_record: "stressed, deadline, 7/10" (3 weeks ago)
       - chat_message:     "we talked about setting boundaries at work" (1 week ago)
       - breathing_session: "completed box breathing after work stress" (5 days ago)
  3. Format as natural language context block
  4. Inject into system prompt before the base therapeutic instructions
  5. Call GPT-4 with the augmented prompt
```

### How the AgentChatUseCase wires it together

`src/application/chat/use_cases/agent_chat_use_case.py` is the orchestration layer.
It already holds references to both `similarity_search_service` and
`user_knowledge_service` (injected via `__init__`), but does not call them yet. The M3
work adds the RAG call between context building and the LLM call:

```python
# Current flow in AgentChatUseCase.execute (line 49):
response = await self.agent_service.send_message(user_id, agent_type, message, context or {})

# Post-M3 flow (planned):
rag_chunks = await self.rag_context_builder.build_rag_context(user_id, message)
enriched_context = {**(context or {}), "rag_chunks": rag_chunks}
response = await self.agent_service.send_message(user_id, agent_type, message, enriched_context)
```

---

## Common mistakes and how to avoid them

**1. Context window overflow — retrieving too many chunks**

Retrieving 20 chunks to "be safe" will balloon your prompt past GPT-4's limit. The fix is
to set a firm token budget. Retrieve top-3 to top-5 chunks, format them as short summaries
(not full record objects), and measure total tokens before the API call.

```python
# WRONG — no limit, could overflow context
chunks = await similarity_search.find_similar_content(user_id, tags, limit=20)

# CORRECT — bounded retrieval, short format
chunks = await similarity_search.find_similar_content(user_id, tags, limit=5)
context_block = "\n".join(
    f"[{c.source_type} {c.created_at.date()}] {c.content_preview[:200]}"
    for c in chunks
)
```

**2. Stale embeddings — embeddings not updated after edits**

If a user edits an emotional record, the pgvector embedding for that record still reflects
the old text. Retrieval will find semantically incorrect results. The fix is to trigger
re-embedding as part of the record update path, not just creation. Tag Celery tasks with
`source_id` so you can upsert rather than duplicate.

**3. Retrieval latency blocking the user response**

An async pgvector query is fast (low single-digit milliseconds on a warm index), but an
OpenAI embeddings API call is a network round-trip (~100–200ms). Do not call the embeddings
API in the critical path if you can pre-compute. The M3 plan pre-generates embeddings via
Celery when records are saved, so at chat time you only run the pgvector search.

If you must embed at query time (e.g. for the search endpoint), run it with `asyncio.gather`
in parallel with other setup work rather than sequentially:

```python
# SLOW — sequential
query_embedding = await embedding_service.embed(message)
user_profile    = await user_repository.get_by_id(user_id)
recent_messages = await conversation_repository.get_recent_context(...)

# FAST — parallel
query_embedding, user_profile, recent_messages = await asyncio.gather(
    embedding_service.embed(message),
    user_repository.get_by_id(user_id),
    conversation_repository.get_recent_context(...)
)
```

**4. Privacy leak — user A's embeddings retrieved for user B**

Every similarity search query MUST include `user_id` in the WHERE clause. pgvector does
not enforce row-level security by default. If you forget the user filter, a semantic query
from user A could surface emotionally sensitive records from user B.

The `ISimilaritySearchService` interface (`src/application/services/similarity_search_service.py`
line 36) enforces this by requiring `user_id` as the first parameter on every method. Do
not add methods that omit it. Add the following to pgvector queries explicitly:

```python
# WRONG — missing user scope
WHERE embedding <-> :query_vec ORDER BY ... LIMIT 5

# CORRECT — always scoped to the authenticated user
WHERE user_id = :user_id
  AND embedding <-> :query_vec ORDER BY ... LIMIT 5
```

**5. Treating the mock as validated behaviour**

`MockSimilaritySearchService` (`src/infrastructure/services/mock_similarity_search_service.py`)
returns empty lists and hardcoded mock data. Tests written against the mock prove nothing
about retrieval quality. Write integration tests against the real pgvector implementation
using a test database with known embeddings. Assert cosine similarity scores are above your
threshold, not just that the list is non-empty.

**6. Using keyword search when you need semantic search**

The current similarity logic in the mock uses Jaccard tag overlap (set intersection / union).
This is keyword matching, not semantic matching. "Overwhelmed" and "anxious" share no tags
but are semantically close. PostgreSQL full-text search (`tsvector`, `tsquery`) has the same
limitation. Only vector embeddings capture meaning across synonyms and paraphrasing.

---

## Further reading

**LangChain:**
- [LangChain RAG concepts](https://python.langchain.com/docs/concepts/rag/) — official explanation of the retrieve-augment-generate loop, chain types, and retriever abstractions
- [LangChain retrievers](https://python.langchain.com/docs/how_to/#retrievers) — how to wrap any data source as a retriever, including pgvector

**OpenAI:**
- [OpenAI cookbook — RAG](https://cookbook.openai.com/examples/question_answering_using_embeddings) — practical notebook showing embeddings, cosine similarity, and prompt construction
- [Embeddings API reference](https://platform.openai.com/docs/guides/embeddings) — token limits per model, choosing between `text-embedding-3-small` (1536 dims, cheaper) and `text-embedding-3-large` (3072 dims, more accurate)

**pgvector:**
- [pgvector GitHub README](https://github.com/pgvector/pgvector) — installation, index types (HNSW vs IVFFlat), distance operators (`<->`, `<=>`, `<#>`)
- [pgvector Python asyncpg example](https://github.com/pgvector/pgvector-python#asyncpg) — how to register the vector type with asyncpg so SQLAlchemy async sessions work correctly

**Semantic vs keyword search:**
- Keyword search (full-text, Jaccard, BM25) matches exact words. Fast, interpretable, misses synonyms.
- Semantic search (embeddings + cosine similarity) matches meaning. Slower to set up, handles synonyms, paraphrase, and cross-language matches. Required for a mental health context where users describe the same feeling with very different words.
- For EmotionAI, semantic search is the right default. Keyword search is a useful secondary signal when filtering by emotion label or date range before handing results to the vector ranker.
