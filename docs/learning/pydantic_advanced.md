# Pydantic v2 Advanced Patterns — EmotionAI study guide

## What is it and why do we use it here

Pydantic v2 is a data validation and serialization library for Python. You define a class
that inherits from `BaseModel`, annotate fields with types, and Pydantic enforces those
types on every instantiation — raising `ValidationError` when data is wrong.

EmotionAI migrated its DTOs from plain dataclasses to Pydantic `BaseModel` in Phase 02
for three concrete reasons:

**1. `__post_init__` ValueError becomes HTTP 500, not 422.**
With a dataclass, validation logic lives in `__post_init__`:

```python
# BEFORE: dataclass approach
@dataclass
class ChatRequest:
    message: str
    agent_type: str

    def __post_init__(self):
        if not self.message.strip():
            raise ValueError("Message cannot be empty or whitespace")
```

FastAPI doesn't know about `ValueError` from `__post_init__`. It propagates as an
unhandled exception and becomes HTTP 500. The client gets a generic server error
instead of a structured field-level message telling them what they sent wrong.

**2. Pydantic integrates natively with FastAPI for structured 422 responses.**
FastAPI catches `pydantic.ValidationError` automatically and converts it to an
HTTP 422 response with a `detail` array — one entry per failing field. The client
knows exactly which field failed, what value was given, and why.

**3. Type coercion, JSON schema generation, and OpenAPI integration are free.**
Pydantic coerces compatible types (`"42"` → `42` for an `int` field), generates
JSON schema automatically, and FastAPI uses that schema to power OpenAPI docs.

This project uses **Pydantic 2.12.5** (pinned in `requirements.txt`) alongside
**pydantic-settings 2.x** for configuration management.

---

## How it works conceptually (explain as if to a junior developer)

### The validator lifecycle

When you create a Pydantic model instance (e.g., `ChatRequest(**data)`), Pydantic
runs these steps in order:

```
Raw input dict
    │
    ▼
1. @field_validator(mode='before')   — raw value, before type coercion
    │
    ▼
2. Type coercion                     — "42" → 42, "true" → True
    │
    ▼
3. Type check                        — fails if coercion is impossible
    │
    ▼
4. @field_validator(mode='after')    — typed, coerced value
    │
    ▼
5. @model_validator(mode='after')    — all fields available as self.field_name
    │
    ▼
Model instance
```

### mode='before' vs mode='after'

`mode='before'` receives the raw value before type coercion — useful when you need
to transform the input itself (e.g., split a comma-separated string into a list).
But the value is still raw: it could be a string, a dict, or None.

`mode='after'` receives the typed, already-coerced value. You get the actual Python
type you declared (`str`, `int`, `UUID`, etc.). This is safer for validation logic.

```python
# mode='before' — receives raw, transforms for type coercion
@field_validator("trusted_hosts", mode="before")
@classmethod
def _parse_trusted_hosts(cls, v):
    if isinstance(v, str):               # v is raw string from env var
        items = [s.strip() for s in v.split(",") if s.strip()]
        return items or ["*"]
    return v

# mode='after' — receives typed str, validates its content
@field_validator("message")
@classmethod
def message_not_whitespace(cls, v: str) -> str:
    if not v.strip():                    # v is guaranteed to be a str here
        raise ValueError("Message cannot be empty or whitespace")
    return v
```

### How FastAPI converts ValidationError to 422

FastAPI wraps every route handler in a try/except for `pydantic.ValidationError`.
When Pydantic raises it, FastAPI serializes the error as:

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "message"],
      "msg": "Value error, Message cannot be empty or whitespace",
      "input": "   "
    }
  ]
}
```

The Flutter client receives a machine-readable error identifying exactly which field
failed — not a generic "Internal Server Error".

### ConfigDict and model_config

Pydantic v2 replaced the inner `class Config` pattern with `model_config`:

```python
# OLD: Pydantic v1 inner class (still works but deprecated)
class MyModel(BaseModel):
    name: str
    class Config:
        frozen = True

# NEW: Pydantic v2 model_config
class MyModel(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
```

`ConfigDict` is a typed dict — your IDE can autocomplete valid options and catch
invalid configuration keys at development time.

### @field_serializer — controlling output

`@field_serializer` controls how a field appears in `model_dump()` and JSON responses.
Without it, a `datetime` field serializes to a Python `datetime` object; FastAPI then
applies its own default serialization. With it, you control the exact output format.

### Literal types — compile-time string enums

`Literal["therapy", "wellness"]` restricts a field to exactly those string values.
Any other value triggers a 422 with a clear error message. It's lighter than `Enum`
for small fixed sets and readable in OpenAPI docs.

---

## Key patterns used in this project (with code examples from the actual codebase)

### 1. @field_validator — whitespace validation in chat_dtos.py

From `src/application/dtos/chat_dtos.py` and `src/presentation/api/routers/chat.py`:

```python
from pydantic import BaseModel, ConfigDict, Field, field_validator

class ChatApiRequest(BaseModel):
    agent_type: Literal["therapy", "wellness"] = "therapy"
    message: str = Field(..., min_length=1, max_length=700)

    @field_validator("message")
    @classmethod                          # required in Pydantic v2
    def message_not_whitespace(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message cannot be empty or whitespace")
        return v                          # always return the (possibly modified) value
```

Line by line:
- `@field_validator("message")` — declares which field this validator applies to
- `@classmethod` — required by Pydantic v2; omitting it causes a `PydanticUserError`
- `cls` parameter — the model class (not an instance); use `cls` not `self`
- `v: str` — the value arrives already coerced to `str` because default mode is `after`
- `raise ValueError(...)` — Pydantic catches this and wraps it in `ValidationError`
- `return v` — you must return the value (even unmodified); omitting it sets the field to `None`

### 2. Field constraints — intensity validation in chat_dtos.py

```python
class EmotionalRecordRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_id: UUID
    emotion_type: str
    intensity: int = Field(..., ge=1, le=10)   # 1 ≤ intensity ≤ 10
```

`Field(...)` means the field is required (no default). `ge=1` means "greater than or
equal to 1"; `le=10` means "less than or equal to 10". Pydantic enforces these before
any `@field_validator` runs. A value of `0` or `11` produces a 422 automatically —
no custom validator code needed.

Other useful constraints: `gt` (strictly greater), `lt` (strictly less), `min_length`,
`max_length`, `pattern` (regex).

### 3. Literal types — agent_type in chat_dtos.py

```python
class ChatRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_id: UUID
    message: str = Field(..., min_length=1, max_length=2000)
    agent_type: Literal["therapy", "wellness"] = "therapy"
```

If a client sends `agent_type: "coaching"`, Pydantic raises a `ValidationError` and
FastAPI returns:

```json
{
  "detail": [
    {
      "type": "literal_error",
      "loc": ["body", "agent_type"],
      "msg": "Input should be 'therapy' or 'wellness'",
      "input": "coaching"
    }
  ]
}
```

### 4. @model_validator — cross-field validation in profile_dtos.py

From `src/application/dtos/profile_dtos.py`:

```python
from typing import Self
from pydantic import BaseModel, Field, model_validator

class UserProfileRequest(BaseModel):
    first_name: Optional[str] = Field(None, ...)
    last_name: Optional[str] = Field(None, ...)
    username: Optional[str] = Field(None, ...)
    # ... 9 more optional fields

    @model_validator(mode='after')
    def at_least_one_field_provided(self) -> Self:
        fields_to_check = [
            'first_name', 'last_name', 'username', 'date_of_birth',
            'phone_number', 'address', 'occupation', 'emergency_contact',
            'medical_info', 'therapy_preferences', 'user_profile_data', 'terms_accepted'
        ]
        if all(getattr(self, f) is None for f in fields_to_check):
            raise ValueError("At least one profile field must be provided")
        return self                        # always return self in mode='after'
```

Key difference from `@field_validator`: `mode='after'` on `@model_validator` gives
you access to all fields via `self.field_name`. You can check relationships between
fields — something that's impossible in a single-field validator.

`-> Self` return type is the idiomatic Pydantic v2 annotation for `@model_validator(mode='after')`.
Import `Self` from `typing` (Python 3.11+) or `typing_extensions`.

### 5. @field_serializer — custom timestamp output in chat.py

From `src/presentation/api/routers/chat.py`:

```python
from pydantic import BaseModel, field_serializer

class ChatApiResponse(BaseModel):
    message: str
    agent_type: str
    conversation_id: Optional[str] = None
    suggestions: List[str] = []
    timestamp: datetime                    # stored as datetime object

    @field_serializer("timestamp")
    def serialize_timestamp(self, v: datetime) -> str:
        return v.isoformat()              # ISO 8601 string in JSON output
```

Without `@field_serializer`, FastAPI would apply its own datetime serialization
(which varies by configuration). With it, the Flutter client always receives a
consistent ISO 8601 string — no manual `.isoformat()` scattered across callers.

Before this pattern, EmotionAI had `timestamp: str` and called `.isoformat()` at
the point of construction. Now the model owns its serialization.

### 6. model_config = SettingsConfigDict in settings.py

From `src/infrastructure/config/settings.py`:

```python
# BEFORE: pydantic-settings v1 inner class
class Settings(BaseSettings):
    class Config:
        env_file = ".env"
        case_sensitive = False

# AFTER: pydantic-settings v2 SettingsConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env" if os.getenv("ENVIRONMENT", "development") == "development"
                else "/etc/emotionai-api.env",
        case_sensitive=False,
        env_prefix="",
        extra="ignore",
    )
```

`SettingsConfigDict` is the pydantic-settings v2 equivalent of `ConfigDict` — it
adds settings-specific options like `env_file`, `env_prefix`, and `extra="ignore"`
(silently ignore unknown environment variables).

The migration also handles `trusted_hosts` with `Union[List[str], str]` to support
comma-separated env var values:

```python
trusted_hosts: Union[List[str], str] = Field(default_factory=lambda: ["*"], env="TRUSTED_HOSTS")

@field_validator("trusted_hosts", mode="before")
@classmethod
def _parse_trusted_hosts(cls, v):
    if isinstance(v, str):
        items = [s.strip() for s in v.split(",") if s.strip()]
        return items or ["*"]
    return v
```

### 7. ConfigDict(frozen=True) — immutable DTOs

Every request DTO in this project uses `frozen=True`:

```python
class ChatRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    user_id: UUID
    message: str
```

`frozen=True` makes the model instance immutable — attempting to set an attribute
after construction raises `ValidationError`. It also makes the model hashable (useful
when storing DTOs in sets or as dict keys). This replaces `@dataclass(frozen=True)`.

---

## Common mistakes and how to avoid them

**1. Using `mode='before'` when you need typed field access**

In `mode='before'`, the value hasn't been coerced yet — you're working with raw input.

```python
# WRONG: expects str, but mode='before' might receive a dict or None
@field_validator("email", mode="before")
@classmethod
def normalize_email(cls, v: str) -> str:
    return v.lower()   # AttributeError if v is None

# RIGHT: use mode='after' (default) for typed access
@field_validator("email")
@classmethod
def normalize_email(cls, v: str) -> str:
    return v.lower()   # v is guaranteed str here
```

**2. Forgetting `@classmethod` on `@field_validator` methods**

Pydantic v2 requires `@classmethod` on all `@field_validator` methods. Omitting it
raises `PydanticUserError: `classmethod` decorator should be applied to a classmethod`.
The decorator order matters: `@field_validator` first, then `@classmethod`.

```python
# WRONG: missing @classmethod
@field_validator("message")
def message_not_whitespace(cls, v: str) -> str:  # raises PydanticUserError

# RIGHT
@field_validator("message")
@classmethod
def message_not_whitespace(cls, v: str) -> str:
    ...
```

**3. Raising `ValueError` inside a route handler instead of using Pydantic validators**

```python
# WRONG: ValueError in route body → HTTP 500
@router.post("/chat")
async def chat_with_agent(payload: ChatApiRequest):
    if not payload.message.strip():
        raise ValueError("Empty message")   # → 500 Internal Server Error

# RIGHT: validate in the Pydantic model → HTTP 422
class ChatApiRequest(BaseModel):
    @field_validator("message")
    @classmethod
    def message_not_whitespace(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message cannot be empty or whitespace")
        return v
```

The route handler only fires after validation passes. Push validation to the model.

**4. Mixing `class Config` and `model_config` on the same model**

Defining both causes confusing precedence — which one wins depends on Pydantic
internals and may silently ignore one of them. Pick one and be consistent.

```python
# WRONG: both defined
class MyModel(BaseModel):
    model_config = ConfigDict(frozen=True)
    class Config:           # ignored or causes a PydanticUserError
        frozen = False

# RIGHT: use only model_config in Pydantic v2
class MyModel(BaseModel):
    model_config = ConfigDict(frozen=True)
```

**5. Using `.dict()` instead of `.model_dump()`**

`.dict()` is deprecated in Pydantic v2 and will be removed in v3. Use `.model_dump()`
instead. Similarly, `.json()` is replaced by `.model_dump_json()`.

```python
# DEPRECATED in v2
data = request.dict()
json_str = request.json()

# CORRECT in v2
data = request.model_dump()
json_str = request.model_dump_json()
```

EmotionAI's profile router previously used a `_safe_model_to_dict()` shim that called
`.dict()`. Phase 02 replaced this with direct `.model_dump()` calls throughout.

---

## Further reading

- Pydantic v2 validators docs: https://docs.pydantic.dev/latest/concepts/validators/
- Pydantic v2 serializers docs: https://docs.pydantic.dev/latest/concepts/serializers/
- Pydantic v2 config docs: https://docs.pydantic.dev/latest/concepts/config/
- Pydantic v2 migration guide: https://docs.pydantic.dev/latest/migration/
- FastAPI request validation: https://fastapi.tiangolo.com/tutorial/body-fields/
