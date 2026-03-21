# SQLAlchemy 2.0 Advanced Patterns — EmotionAI study guide

## What is it and why do we use it here

SQLAlchemy 2.0 is Python's most widely-used ORM. In EmotionAI we use its async
layer — `create_async_engine` + `async_sessionmaker` + `AsyncSession` — because
every route handler, use case, and repository in this codebase is `async def`.

The specific patterns we apply solve concrete problems we ran into (or would have
run into) when building the AI personalization pipeline for M3:

**DetachedInstanceError is the #1 async SQLAlchemy bug.**
By default, SQLAlchemy uses lazy loading: relationship attributes are fetched from
the database only when you access them. In a sync context this works transparently.
In async, the session is usually closed by the time you read a relationship —
SQLAlchemy raises `DetachedInstanceError` because there's no open session to
execute the lazy query. `selectinload` solves this by loading the relationship
eagerly before the session closes.

**hybrid_property avoids adding database columns for derived values.**
`intensity_level` ("low", "medium", "high") is derived from the `intensity` integer
column. Adding a real column would duplicate data and require migration on every
threshold change. A `@hybrid_property` computes the value in Python and optionally
translates it to a SQL expression for use in queries.

**selectinload prevents N+1 queries.**
Loading 50 conversations and then accessing `conv.messages` for each would fire 51
SELECT statements. `selectinload` fires exactly 2: one for conversations, one IN
query for all their messages at once.

**get_session() ensures commit/rollback safety.**
`async_session_factory()` creates a raw session with no lifecycle management.
`get_session()` is an `@asynccontextmanager` that commits on clean exit and
rolls back automatically on exception.

This project uses **SQLAlchemy 2.0.48** with **asyncpg** as the PostgreSQL driver.

---

## How it works conceptually (explain as if to a junior developer)

### Relationship loading strategies

SQLAlchemy has four strategies for loading related objects. Choosing the wrong one
causes either `DetachedInstanceError` (lazy in async) or poor performance.

**Lazy (default) — dangerous in async:**
```
SELECT * FROM conversations WHERE id = ?
-- You access conv.messages later, OUTSIDE the session
-- SQLAlchemy tries: SELECT * FROM messages WHERE conversation_id = ?
-- But the session is already closed → DetachedInstanceError
```

**selectinload — correct for collections (one-to-many):**
```sql
SELECT * FROM conversations WHERE id = ?
SELECT * FROM messages WHERE conversation_id IN (id1, id2, ...)
```
Two queries, but both fire inside the session. Collections stay loaded after the
session closes. Use this for one-to-many relationships.

**joinedload — correct for single related objects (many-to-one / one-to-one):**
```sql
SELECT conversations.*, users.*
FROM conversations
JOIN users ON conversations.user_id = users.id
WHERE conversations.id = ?
```
One query with a JOIN. Use this for scalar relationships. Avoid for collections —
JOINing a one-to-many produces a Cartesian product (row duplication).

**subqueryload — rarely needed:**
Uses a correlated subquery instead of IN. Useful when the IN list would be very large,
but selectinload is almost always the right default.

### hybrid_property: dual nature

A `@hybrid_property` behaves differently depending on whether you access it on an
instance or on the class:

```
record.intensity_level          → Python method runs, returns "low"/"medium"/"high"
select(...).where(EmotionalRecordModel.intensity_level == "low")
                                → SQL expression runs, generates SQL CASE WHEN
```

The Python side handles runtime logic. The `@expression` side (decorated with
`@<property>.expression`) returns a SQLAlchemy column expression for DB-level queries.

### Async session lifecycle

The session is the unit of work — it tracks which objects are new, modified, or
deleted, and flushes them to the database when you commit.

```
async with db.get_session() as session:
    # 1) session is open
    session.add(model)
    await session.commit()     # flush + commit
    # 2) session closed, all objects are expired
    # expire_on_commit=False prevents attributes from being marked expired
    model.id    # still accessible after close because expire_on_commit=False
```

`expire_on_commit=False` means attributes are NOT marked "need refresh" after commit.
Without it, accessing `model.id` after commit triggers a lazy reload — which fails in
async if the session is already closed.

### The select() API (2.0 style)

SQLAlchemy 2.0 deprecated `session.query(Model).filter(...)`. The new API:

```python
# OLD: session.query() — sync-only, deprecated
results = session.query(ConversationModel).filter(ConversationModel.is_active == True).all()

# NEW: select() — async-compatible, composable
from sqlalchemy import select
stmt = select(ConversationModel).where(ConversationModel.is_active == True)
result = await session.execute(stmt)
conversations = result.scalars().all()
```

`session.execute()` returns a `CursorResult`. `.scalars()` unwraps single-column
results into Python objects. `.all()` materializes the list.

---

## Key patterns used in this project (with code examples from the actual codebase)

### 1. hybrid_property: intensity_level in models.py

From `src/infrastructure/database/models.py`:

```python
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import case

class EmotionalRecordModel(Base):
    __tablename__ = 'emotional_records'

    intensity = Column(Integer, nullable=False)   # 1-10 scale stored in DB

    @hybrid_property
    def intensity_level(self) -> str:
        """Human-readable intensity category: low (1-3), medium (4-7), high (8-10)"""
        if self.intensity <= 3:
            return "low"
        elif self.intensity <= 7:
            return "medium"
        return "high"

    @intensity_level.expression
    @classmethod
    def intensity_level(cls):
        return case(
            (cls.intensity <= 3, "low"),
            (cls.intensity <= 7, "medium"),
            else_="high",
        )
```

The Python side (`def intensity_level(self)`) runs on model instances — when you
read `record.intensity_level` in Python code.

The SQL expression side (`@intensity_level.expression`) runs when you use
`EmotionalRecordModel.intensity_level` inside a SQLAlchemy `select()` or `where()`
clause. It generates SQL like:

```sql
CASE
    WHEN intensity <= 3 THEN 'low'
    WHEN intensity <= 7 THEN 'medium'
    ELSE 'high'
END
```

This lets the M3 pipeline do DB-level filtering:
```python
select(EmotionalRecordModel).where(EmotionalRecordModel.intensity_level == "high")
```

### 2. hybrid_property: duration_days in models.py

```python
class ConversationModel(Base):
    __tablename__ = 'conversations'

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    @hybrid_property
    def duration_days(self) -> int:
        """Number of days since conversation was created"""
        if self.created_at is None:
            return 0
        if self.created_at.tzinfo is None:
            delta = datetime.now(timezone.utc) - self.created_at.replace(tzinfo=timezone.utc)
        else:
            delta = datetime.now(timezone.utc) - self.created_at
        return max(0, delta.days)
```

Notice: `duration_days` has **no `@expression` side**. The value depends on
`datetime.now(timezone.utc)` — a live runtime value that changes every second.
There's no reliable way to express this as a portable SQL expression (PostgreSQL has
`CURRENT_TIMESTAMP`, but that would return a different value than Python's `datetime.now`
depending on timezone handling). Decision from Phase 02-03: Python-only is intentional.

### 3. selectinload in the conversation repository

From `src/infrastructure/conversations/repositories/sqlalchemy_conversation_repository.py`:

```python
from sqlalchemy.orm import selectinload

async def get_conversation_with_messages(
    self, conversation_id: str, user_id: uuid.UUID
) -> Optional[Dict[str, Any]]:
    """Get conversation with eagerly loaded messages (avoids N+1)"""
    async with self.db.get_session() as session:
        result = await session.execute(
            select(ConversationModel)
            .where(
                and_(
                    ConversationModel.id == conversation_id,
                    ConversationModel.user_id == str(user_id),
                )
            )
            .options(selectinload(ConversationModel.messages))   # <-- eager load
        )
        conv = result.scalar_one_or_none()
        if not conv:
            return None
        return {
            "id": str(conv.id),
            "messages": [
                {
                    "id": str(m.id),
                    "content": m.content,
                    "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                }
                for m in conv.messages           # safe: messages already loaded
            ],
        }
```

`.options(selectinload(ConversationModel.messages))` tells SQLAlchemy to load `messages`
with a second SELECT using an IN clause — before the session closes. The two SQL
statements it generates:

```sql
-- Query 1: load the conversation
SELECT * FROM conversations
WHERE id = ? AND user_id = ?

-- Query 2: load all messages for that conversation
SELECT * FROM messages
WHERE messages.conversation_id IN (?)
```

`conv.messages` in the loop is safe because all messages are already in memory.

### 4. selectinload for user context in the emotional record repository

From `src/infrastructure/records/repositories/sqlalchemy_emotional_repository.py`:

```python
async def get_by_user_id_with_user(
    self,
    user_id: UUID,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Get emotional records with eagerly loaded user (avoids DetachedInstanceError)"""
    async with self.db.get_session() as session:
        query = (
            select(EmotionalRecordModel)
            .where(EmotionalRecordModel.user_id == user_id)
            .options(selectinload(EmotionalRecordModel.user))    # <-- eager load user
            .order_by(EmotionalRecordModel.recorded_at.desc())
        )
        if limit is not None:
            query = query.limit(limit)
        result = await session.execute(query)
        rows = result.scalars().all()
        return [_model_to_dict(r) for r in rows]
```

This method exists for the M3 personalization context builder, which needs both the
record data and the user's profile in a single pass. Without `selectinload`, accessing
`record.user.therapy_context` after the session closes would raise `DetachedInstanceError`.

### 5. Session management: get_session() in connection.py

From `src/infrastructure/database/connection.py`:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
    """Get async database session with automatic cleanup"""
    if not self._is_connected:
        await self.connect()

    session = self.async_session_factory()
    try:
        yield session
        await session.commit()      # auto-commit on clean exit
    except Exception as e:
        await session.rollback()    # auto-rollback on any exception
        logger.error(f"Database session error: {e}")
        raise
    finally:
        await session.close()       # always close, even if rollback raised
```

Every repository uses this pattern:

```python
# BEFORE: raw session factory — no automatic rollback
session = self.db.async_session_factory()
session.add(model)
await session.commit()             # if this raises, session is never rolled back
await session.close()              # and session may never be closed

# AFTER: get_session() context manager — safe by default
async with self.db.get_session() as session:
    session.add(model)
    await session.commit()         # explicit commit inside is still safe (idempotent)
```

The explicit `await session.commit()` inside repository methods is intentional — even
though `get_session()` auto-commits on exit. It makes the intent clear at the call site
and is harmless (committing an already-committed transaction is a no-op).

### 6. Relationship definitions in UserModel (models.py)

```python
class UserModel(Base):
    __tablename__ = 'users'

    # One-to-many: one user has many conversations
    conversations = relationship(
        "ConversationModel",
        back_populates="user",          # ConversationModel.user points back here
        cascade="all, delete-orphan"    # delete conversations when user is deleted
    )

    # One-to-many: one user has many emotional records
    emotional_records = relationship(
        "EmotionalRecordModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    # One-to-one: one user has at most one profile_data row
    profile_data = relationship(
        "UserProfileDataModel",
        back_populates="user",
        uselist=False,                  # returns single object, not list
        cascade="all, delete-orphan"
    )

    # One-to-one: one user has at most one agent_personality row
    agent_personality = relationship(
        "AgentPersonalityModel",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
```

Key parameters:
- `back_populates="user"` — bidirectional: sets `ConversationModel.user` automatically
- `cascade="all, delete-orphan"` — deleting a `UserModel` also deletes all related rows
- `uselist=False` — makes the relationship return a single object (not a list), used for
  one-to-one relationships like `profile_data` and `agent_personality`

---

## Common mistakes and how to avoid them

**1. Accessing lazy-loaded relationship outside async session (DetachedInstanceError)**

```python
# WRONG: session closes, then you access .messages
async with db.get_session() as session:
    conv = await session.scalar(select(ConversationModel).where(...))
# session is now closed
print(conv.messages)    # DetachedInstanceError: Instance <ConversationModel> is not bound to a Session

# RIGHT: load eagerly inside the session
async with db.get_session() as session:
    result = await session.execute(
        select(ConversationModel)
        .where(...)
        .options(selectinload(ConversationModel.messages))
    )
    conv = result.scalar_one_or_none()
print(conv.messages)    # safe: already loaded
```

**2. Using joinedload for one-to-many collections (Cartesian product)**

```python
# WRONG: joinedload on a collection duplicates parent rows
from sqlalchemy.orm import joinedload
select(UserModel).options(joinedload(UserModel.emotional_records))
# If user has 100 emotional records → 100 UserModel rows in the result
# Deduplication via .unique() is required — easy to forget

# RIGHT: selectinload for collections
from sqlalchemy.orm import selectinload
select(UserModel).options(selectinload(UserModel.emotional_records))
# Two queries, no duplication
```

**3. Using async_session_factory() directly instead of get_session()**

```python
# WRONG: no automatic rollback on exception
session = self.db.async_session_factory()
try:
    session.add(model)
    await session.commit()
except:
    pass    # session left in dirty state, not rolled back or closed

# RIGHT: always use get_session()
async with self.db.get_session() as session:
    session.add(model)
    await session.commit()
# auto-commits, auto-rollbacks, and always closes
```

**4. Forgetting `expire_on_commit=False` in the session maker**

```python
# If expire_on_commit is True (default):
async with db.get_session() as session:
    user = await session.scalar(select(UserModel).where(...))
    await session.commit()
    print(user.email)   # AttributeError or lazy-load attempt: attribute expired post-commit

# EmotionAI sets expire_on_commit=False in connect():
self.async_session_factory = async_sessionmaker(
    bind=self.async_engine,
    expire_on_commit=False    # attributes remain accessible after commit
)
```

**5. Using legacy session.query() API instead of select()**

`session.query()` is from SQLAlchemy 1.x. It's not async-compatible and is deprecated:

```python
# DEPRECATED / sync only
results = session.query(EmotionalRecordModel).filter(
    EmotionalRecordModel.user_id == user_id
).all()

# CORRECT: SQLAlchemy 2.0 style
stmt = select(EmotionalRecordModel).where(EmotionalRecordModel.user_id == user_id)
result = await session.execute(stmt)
rows = result.scalars().all()
```

**6. Defining hybrid_property SQL expression that doesn't match Python logic**

```python
# DANGEROUS: Python says "low" ≤ 3, SQL expression says "low" ≤ 4
@hybrid_property
def intensity_level(self) -> str:
    if self.intensity <= 3:   # Python threshold: 3
        return "low"

@intensity_level.expression
@classmethod
def intensity_level(cls):
    return case(
        (cls.intensity <= 4, "low"),  # SQL threshold: 4 — BUG
        ...
    )
```

A mismatch means `.filter(Model.intensity_level == "low")` returns different records
than iterating and checking `record.intensity_level == "low"`. Always keep the two
sides in sync and add a test that verifies both paths.

---

## Further reading

- SQLAlchemy 2.0 relationship loading: https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html
- SQLAlchemy hybrid properties: https://docs.sqlalchemy.org/en/20/orm/extensions/hybrid.html
- SQLAlchemy async session: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- SQLAlchemy 2.0 migration guide: https://docs.sqlalchemy.org/en/20/changelog/migration_20.html
- asyncpg + SQLAlchemy best practices: https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#module-sqlalchemy.dialects.postgresql.asyncpg
