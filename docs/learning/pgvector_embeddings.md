# pgvector + Embeddings — EmotionAI study guide

## What is it and why do we use it here

An embedding is a list of numbers — a vector — that encodes the meaning of a piece of text. Two texts that mean similar things end up with vectors that are mathematically close. Two unrelated texts end up far apart. This is the foundation of semantic search: instead of matching keywords, you find records whose meaning is similar to a query.

EmotionAI needs this because mental health data is inherently imprecise. A user might write "I feel hollow and disconnected" in one session and "I just feel nothing, like I'm not really here" in another. A keyword search finds no overlap. A vector similarity search recognises both as semantically proximate.

Milestone 3 will use these vectors to power:

- Finding past messages or emotional records similar to a current user input
- Personalised context retrieval for the LangChain therapy agent
- Pattern detection across a user's emotional history

**Why pgvector and not a dedicated vector database (Qdrant, Pinecone, Weaviate)?**

EmotionAI already runs PostgreSQL 16 on RDS. Adding a dedicated vector store would mean:

- A second service to provision in Terraform
- A second connection pool to manage in the container
- Data sync between Postgres (authoritative) and the vector store (search index)
- A second failure domain for a t3.micro budget environment

pgvector keeps vectors in the same rows as the data they belong to. A query like "find emotional records similar to this text, for this user, recorded in the last 30 days" is a single SQL query with a join — no cross-service coordination, no dual writes. The tradeoff is that pgvector's approximate nearest-neighbor (ANN) performance does not scale to billions of vectors. EmotionAI will never have billions of rows per user, so the tradeoff is correct here.

This is the same reasoning pattern as using SQLite for mobile rather than spinning up a server: match the tool to the scale.

## How it works conceptually

### Step 1 — Text becomes a vector

Call the OpenAI embeddings API with a piece of text:

```python
response = openai_client.embeddings.create(
    input="I feel hollow and disconnected",
    model="text-embedding-ada-002"
)
vector = response.data[0].embedding  # a list of 1536 floats
```

The model always returns exactly 1536 numbers. That number is the dimension count — it never changes for `text-embedding-ada-002`. Every piece of text you embed gets the same-length vector, which is why you can compare them.

### Step 2 — Vectors are stored as a column

pgvector adds a native `vector` type to PostgreSQL. A `vector(1536)` column stores exactly 1536 floats per row — about 6 KB per row in raw form, stored efficiently by the extension.

### Step 3 — Similarity search uses distance operators

pgvector adds three distance operators:

| Operator | Distance function | Use case |
|----------|-------------------|----------|
| `<->` | L2 (Euclidean) | Geometric closeness |
| `<#>` | Negative inner product | Dot-product similarity |
| `<=>` | Cosine distance | Meaning similarity regardless of magnitude |

For text embeddings, **cosine distance is the right choice**. Cosine distance measures the angle between two vectors — it does not care how long the vectors are, only what direction they point. Two sentences that mean the same thing point in roughly the same direction even if one is a short phrase and one is a long paragraph. Euclidean distance would penalise that length difference unfairly.

A cosine similarity of 1.0 means identical direction (identical meaning). A value of 0.0 means perpendicular (completely unrelated). In practice, for well-encoded semantically similar content you'll see values above 0.85.

Translated to SQL:

```sql
SELECT id, content, 1 - (embedding_vector <=> '[0.02, -0.14, ...]'::vector) AS similarity
FROM messages
WHERE user_id = 'abc123'
ORDER BY embedding_vector <=> '[0.02, -0.14, ...]'::vector
LIMIT 10;
```

`<=>` returns the cosine *distance* (lower is more similar). Subtracting from 1 gives you cosine *similarity* (higher is more similar). The `ORDER BY` sorts by distance ascending so the most similar rows come first.

### Step 4 — Approximate nearest neighbor (ANN)

An exact nearest-neighbor search scans every row and computes every distance. For millions of rows that is too slow.

pgvector supports two ANN index types:

- **IVFFlat**: divides vectors into lists and searches only a subset of them. Faster at query time, some recall loss, good for large static datasets.
- **HNSW** (Hierarchical Navigable Small World): builds a layered graph structure. Better recall, faster at query time for EmotionAI's typical read/write mix, more memory usage.

EmotionAI's embedding columns do not have vector indexes yet — that is M3 work. For a user's personal dataset (hundreds to low thousands of rows) a sequential scan is fast enough and avoids premature optimisation. The HNSW index creation syntax for future reference:

```sql
CREATE INDEX idx_messages_embedding_hnsw
ON messages USING hnsw (embedding_vector vector_cosine_ops);
```

## Key patterns used in this project

### The migration: enabling the extension and adding columns

Migration `005` at [`migrations/versions/005_add_embedding_vectors.py`](/home/eager-eagle/code/emotionai/emotionai-api/migrations/versions/005_add_embedding_vectors.py) does three things:

```python
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = '005_embedding_vectors'
down_revision = '004_unique_pattern'


def upgrade() -> None:
    # Enable pgvector extension (idempotent)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Vector(1536) matches OpenAI text-embedding-ada-002 output dimensions
    op.add_column('messages',
        sa.Column('embedding_vector', Vector(1536), nullable=True)
    )

    op.add_column('emotional_records',
        sa.Column('embedding_vector', Vector(1536), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('emotional_records', 'embedding_vector')
    op.drop_column('messages', 'embedding_vector')
    # Do NOT drop the vector extension — other objects may depend on it
```

**Why `IF NOT EXISTS` for the extension?** Alembic migrations run across multiple environments: local docker-compose, CI, staging, production. The extension creation is idempotent — safe to run twice. Without `IF NOT EXISTS`, a second `alembic upgrade head` run would crash with `extension "vector" already exists`.

**Why `nullable=True`?** These columns are schema preparation for M3. Existing rows will have NULL in `embedding_vector` until the M3 embedding pipeline processes them. Making them NOT NULL would require backfilling every existing row in the same migration — which could take significant time on production and risks a partial-migration failure. The nullable approach separates schema deployment from data migration.

**Why the extension before the columns?** The `Vector` type does not exist in PostgreSQL until the extension is loaded. If you run `op.add_column` with `Vector(1536)` before `CREATE EXTENSION`, the migration fails. Order matters.

### The ORM models

[`src/infrastructure/database/models.py`](/home/eager-eagle/code/emotionai/emotionai-api/src/infrastructure/database/models.py) imports the `Vector` type from the `pgvector` Python package and declares the column in two models:

```python
from pgvector.sqlalchemy import Vector

class MessageModel(Base):
    __tablename__ = 'messages'

    # ... other columns ...

    # Intelligent tagging system
    tags = Column(JSONB, nullable=True)
    tag_confidence = Column(Float, nullable=True)
    processed_for_tags = Column(Boolean, default=False, nullable=False)

    # M3 semantic search — nullable until embedding pipeline populates
    embedding_vector = Column(Vector(1536), nullable=True)
```

```python
class EmotionalRecordModel(Base):
    __tablename__ = 'emotional_records'

    # ... other columns ...

    processed_for_tags = Column(Boolean, default=False, nullable=False)

    # M3 semantic search — nullable until embedding pipeline populates
    embedding_vector = Column(Vector(1536), nullable=True)
```

`BreathingSessionModel` deliberately does not have `embedding_vector`. Breathing session content (pattern name, duration, effectiveness rating) is structured numeric data — semantic search over it adds little value and wastes embedding API calls.

### How it fits Clean Architecture

The embedding column lives at the infrastructure layer (`models.py`). The Clean Architecture dependency rule means:

- **Domain layer** (`src/domain/`): knows nothing about vectors. Domain entities like `EmotionalRecord` in `src/domain/entities/` describe the business concept without any vector fields.
- **Application layer** (`src/application/`): use cases will receive plain text and ask an embedding service interface to produce a vector. The interface lives here; the OpenAI implementation lives in infrastructure.
- **Infrastructure layer** (`src/infrastructure/`): `models.py` stores the vector. A future `OpenAIEmbeddingService` in `src/infrastructure/services/` will call the OpenAI embeddings API and return a list of floats. Repositories in `src/infrastructure/repositories/` will accept those floats and run `<=>` similarity queries via SQLAlchemy.
- **Presentation layer** (`src/presentation/api/routers/`): routes receive a text query, call the use case, and return ranked results to the client. No embedding logic here.

The dependency flow for a future semantic search request will be:

```
Router → SearchSimilarRecordsUseCase → EmbeddingServiceInterface
                                     → EmotionalRecordRepositoryInterface

Infrastructure provides:
  OpenAIEmbeddingService (implements EmbeddingServiceInterface)
  SqlAlchemyEmotionalRecordRepository (implements EmotionalRecordRepositoryInterface)
```

### The docker-compose image swap

[`docker-compose.yml`](/home/eager-eagle/code/emotionai/emotionai-api/docker-compose.yml) uses `pgvector/pgvector:pg16` instead of the previous `postgres:13`:

```yaml
db:
  image: pgvector/pgvector:pg16   # was: postgres:13
```

This image is the official pgvector distribution — standard PostgreSQL 16 with the `vector` extension pre-compiled and available. No manual `CREATE EXTENSION` bootstrap scripts are needed in the container; the extension just needs to be enabled per-database via the migration.

### The Python package

[`requirements.txt`](/home/eager-eagle/code/emotionai/emotionai-api/requirements.txt) declares:

```
pgvector>=0.4.0  # SQLAlchemy Vector type for embedding columns
```

This package does two things: provides the `Vector` SQLAlchemy type (used in `models.py` and migrations) and provides async-compatible result handling when reading vector columns back from PostgreSQL via asyncpg.

### The integration test

[`tests/integration/test_pgvector_migration.py`](/home/eager-eagle/code/emotionai/emotionai-api/tests/integration/test_pgvector_migration.py) verifies ORM model metadata without needing a live PostgreSQL instance:

```python
def test_embedding_vector_columns_exist():
    from src.infrastructure.database.models import MessageModel, EmotionalRecordModel

    msg_columns = {c.name for c in MessageModel.__table__.columns}
    assert "embedding_vector" in msg_columns

    er_columns = {c.name for c in EmotionalRecordModel.__table__.columns}
    assert "embedding_vector" in er_columns


def test_embedding_vector_columns_are_nullable():
    from src.infrastructure.database.models import MessageModel, EmotionalRecordModel

    for model, name in [(MessageModel, "MessageModel"), (EmotionalRecordModel, "EmotionalRecordModel")]:
        col = model.__table__.columns["embedding_vector"]
        assert col.nullable is True


def test_breathing_session_model_has_no_embedding_vector():
    from src.infrastructure.database.models import BreathingSessionModel

    bs_columns = {c.name for c in BreathingSessionModel.__table__.columns}
    assert "embedding_vector" not in bs_columns
```

The test suite uses SQLAlchemy's `__table__.columns` metadata introspection — it reads the ORM class definition, not the live database. This avoids the SQLite/pgvector incompatibility that would occur if the test conftest tried to create a `vector(1536)` column in an in-memory SQLite test database.

## Common mistakes and how to avoid them

### 1. Wrong dimension size

Bad:

```python
embedding_vector = Column(Vector(768), nullable=True)
```

Why this fails:

- `text-embedding-ada-002` always returns 1536 dimensions
- If you store a 1536-float vector into a `vector(768)` column, PostgreSQL raises a dimension mismatch error
- If you later switch models (e.g., `text-embedding-3-small` at 1536 or 3072 dims), the stored vectors are incompatible with the column — you must migrate

Always match the column dimension to the model's output dimension. For `text-embedding-ada-002` that is `Vector(1536)`. Document the model name in a comment on the column:

```python
# Vector(1536) matches OpenAI text-embedding-ada-002 output dimensions
embedding_vector = Column(Vector(1536), nullable=True)
```

### 2. Forgetting to enable the extension before the migration runs

Bad migration order:

```python
def upgrade() -> None:
    op.add_column('messages',
        sa.Column('embedding_vector', Vector(1536), nullable=True)
    )
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")  # too late
```

Why this fails:

- The `vector` type does not exist in PostgreSQL until the extension is loaded
- `op.add_column` with `Vector(1536)` translates to `ALTER TABLE messages ADD COLUMN embedding_vector vector(1536)` — PostgreSQL evaluates this immediately and raises `type "vector" does not exist`

Correct order: always `CREATE EXTENSION` before any `op.add_column` that uses `Vector`. See the actual migration at [`migrations/versions/005_add_embedding_vectors.py`](/home/eager-eagle/code/emotionai/emotionai-api/migrations/versions/005_add_embedding_vectors.py).

### 3. Using the wrong docker-compose image in development

If you clone the repo and run `docker-compose up` against an old `postgres:13` image, you will see this when running migrations:

```
sqlalchemy.exc.ProgrammingError: (asyncpg.exceptions.UndefinedObjectError)
type "vector" does not exist
```

That is not a code bug — it is the wrong PostgreSQL image. The dev database must use `pgvector/pgvector:pg16`. Check [`docker-compose.yml`](/home/eager-eagle/code/emotionai/emotionai-api/docker-compose.yml):

```yaml
image: pgvector/pgvector:pg16
```

If you switched from `postgres:13`, you must also destroy and recreate the volume because the old data directory is incompatible with pg16:

```bash
docker-compose down -v   # destroys the postgres_data volume
docker-compose up
alembic upgrade head
```

### 4. Nullable vs not-null before the embedding pipeline runs

Making `embedding_vector` NOT NULL prematurely:

```python
embedding_vector = Column(Vector(1536), nullable=False)  # wrong before M3
```

Why this fails:

- Existing rows have no vector data — an immediate NOT NULL constraint would require every existing row to be backfilled atomically with the schema change
- On production, `ALTER TABLE ... ADD COLUMN ... NOT NULL` without a default causes a full-table rewrite in PostgreSQL versions before 11, and still requires instant validation in pg16
- Any new row inserted before the M3 pipeline runs would fail the NOT NULL constraint

The correct approach: keep columns nullable until the M3 embedding pipeline is deployed and has processed all existing rows. Then add a NOT NULL constraint in a separate migration after the backfill is complete.

### 5. L2 distance instead of cosine distance for text embeddings

Bad query:

```python
# Using L2 distance (<->)
results = await session.execute(
    select(MessageModel)
    .where(MessageModel.user_id == user_id)
    .order_by(MessageModel.embedding_vector.l2_distance(query_vector))
    .limit(10)
)
```

Why cosine is better for text:

- L2 distance is sensitive to the magnitude (length) of the vector
- OpenAI embedding vectors are not normalised — longer texts tend to produce longer vectors
- Two messages with similar meaning but different lengths will have a larger L2 distance than expected
- Cosine distance measures the angle between vectors, not the length — it captures directional similarity, which is what "same meaning" corresponds to

Correct query using cosine distance (`<=>`):

```python
# Using cosine distance (<=>)
results = await session.execute(
    select(MessageModel)
    .where(MessageModel.user_id == user_id)
    .order_by(MessageModel.embedding_vector.cosine_distance(query_vector))
    .limit(10)
)
```

When you later add a vector index, use `vector_cosine_ops` to match:

```sql
CREATE INDEX ON messages USING hnsw (embedding_vector vector_cosine_ops);
```

Mixing `vector_l2_ops` index with `<=>` queries (or vice versa) causes PostgreSQL to fall back to a sequential scan, silently negating the index.

### 6. Importing pgvector before the extension check in tests

If your test suite uses SQLite (as EmotionAI's current conftest does), the `Vector` type cannot be reflected back — SQLite has no concept of it. The integration test in this project avoids this by inspecting ORM metadata rather than issuing DDL:

```python
# Safe: reads Python class metadata, no DB DDL
msg_columns = {c.name for c in MessageModel.__table__.columns}
assert "embedding_vector" in msg_columns
```

Do not do this in test setup:

```python
# Dangerous in SQLite-backed tests
Base.metadata.create_all(engine)  # will fail if engine is SQLite
```

Actual live migration testing must be done against a running pgvector-enabled PostgreSQL — the `docker-compose up` flow followed by `alembic upgrade head`.

## Further reading

- pgvector GitHub repository (README has all operators, index types, and full SQL examples): https://github.com/pgvector/pgvector
- OpenAI embeddings guide (model dimensions, use cases, best practices for text-embedding-ada-002 vs newer models): https://platform.openai.com/docs/guides/embeddings
- pgvector Python package (SQLAlchemy integration, asyncpg support, ORM query helpers): https://github.com/pgvector/pgvector-python
- pgvector vs dedicated vector databases — when to use each (Supabase blog, practical comparison at different scales): https://supabase.com/blog/pgvector-vs-pinecone
- PostgreSQL documentation on operator classes (explains why index operator class must match query operator): https://www.postgresql.org/docs/current/indexes-opclass.html
- OpenAI cookbook — embedding long texts and chunking strategies (relevant for M3 when message content exceeds token limits): https://cookbook.openai.com/examples/embedding_long_inputs
