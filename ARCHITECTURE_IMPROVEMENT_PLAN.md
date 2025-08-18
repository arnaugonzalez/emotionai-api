# EmotionAI – Architecture Improvement Plan (LLM + PyTorch, Proactive Support, AWS)

This plan evolves EmotionAI into a personalized, proactive mental wellness assistant. It covers:
- Clean Architecture refactor (feature-oriented) for API and Flutter
- Hybrid intelligence (LLM + PyTorch) for quality, personalization, and cost control
- Proactive notifications and recommendations
- Production-grade AWS deployment (EC2 + RDS baseline, optional Lambdas/SageMaker)
- A hands-on PyTorch learning path inside this project

The approach is incremental, measurable, and privacy-first.

---

## 0) Executive Summary
- Move to feature-first boundaries in both API and Flutter to improve maintainability.
- Keep OpenAI for empathetic chat and structured extraction; add PyTorch micro-models for personalization, consistency checks, and temporal predictions.
- Introduce an `interventions` feature for proactive support; schedule on-device initially.
- Operate on AWS with EC2 + RDS as the baseline; add Lambdas for scheduled jobs and optionally SageMaker/TorchServe for model serving later.
- Define strict JSON output contracts from the LLM, with fail-closed safety behavior.
- Track outcomes and costs; use metrics to iterate and to reduce token spend.

---

## 1) Goals and Non‑Goals

### Goals
- Clean, evolvable architecture with feature-first folder structures
- Hybrid LLM + PyTorch that improves quality and reduces cost
- Proactive, consent-based notifications and simple recommendations
- Strong privacy and safety guarantees; user control of data
- Reliable AWS deployment with minimal ops burden

### Non‑Goals (for now)
- Full LLM fine‑tuning or heavy agent ecosystems
- Complex streaming infra or real-time orchestration beyond need

---

## 2) Clean Architecture: Feature‑Oriented Refactor

Retain four layers (Domain, Application, Infrastructure, Presentation) but group by feature inside each layer.

### Backend target structure
- Domain (business rules only)
  - `src/domain/<feature>/entities.py`, `value_objects.py`, `interfaces.py` (ports)
- Application (use-cases, orchestrations)
  - `src/application/<feature>/use_cases.py`, `dtos.py`, `services.py` (interfaces)
- Infrastructure (adapters)
  - `src/infrastructure/<feature>/repositories/*.py` (SQLAlchemy)
  - `src/infrastructure/<feature>/services/*.py` (OpenAI, PyTorch, notifications)
  - `src/infrastructure/database/models.py` (can be kept central; optionally split per feature)
- Presentation (drivers)
  - `src/presentation/api/routers/<feature>.py`

### Features to carve
- `chat/` – therapy chat, conversation storage
- `tagging/` – LLM tagging; later PyTorch tag consistency
- `usage/` – token usage logging and monthly limits
- `records/` – emotional records
- `breathing/` – breathing sessions and patterns
- `profile/` – user summaries and trends
- `interventions/` – recommendations and notification planning (new)

### Flutter feature‑first layout
- `lib/features/<feature>/{data,domain,presentation,application}`
- `lib/shared/` kept minimal (theme, utilities, common widgets)

### Refactor checklist
- Create feature folders and move interfaces/models per feature
- Update imports; add barrel files only where they reduce coupling
- Add module-level tests for each feature; keep integration tests stable

---

## 3) Hybrid Intelligence: LLM + PyTorch

Split responsibilities for quality and cost control.
- LLM (OpenAI): empathetic responses, summaries, structured extraction (tags, rationales)
- PyTorch (small, efficient models): personalization, ranking, consistency checks, temporal predictions

### PyTorch modules (incremental)
1) Tag Consistency Classifier
   - Input: message + prior tags → predict plausible tags; flag inconsistencies
   - Purpose: reduce hallucinated or unstable tags; smooth user experience
   - Start: rules/keyword baseline → small CNN/DistilBERT → TorchScript export
2) Coping Strategy Recommender (Ranking)
   - Input: recent tags, past outcomes (accepted/skipped), recency features
   - Output: ranked strategies (e.g., “box breathing 2 min”) with scores
   - Start: rule‑based + weights; progress to a learned ranker
3) Temporal Stress Predictor (Time‑series)
   - Input: hour‑of‑week embeddings (168 bins), tag history, recency
   - Output: probability of stress for upcoming windows (24–72h)
   - Use: select notification slots and content type

### Fusion patterns
- RAG + Ranking: LLM proposes; PyTorch reranks → return top‑1
- Predictive Context: PyTorch flags high‑stress windows; LLM crafts short supportive prompts
- Guardrails: PyTorch/rules detect crisis intents → safe templates + resource links

### Serving path
- Phase 1: In‑process CPU TorchScript for minimal ops and low latency
- Phase 2: TorchServe on EC2 or ONNX Runtime for performance
- Phase 3: SageMaker endpoints if scale/latency requirements warrant

---

## 4) Data Model Additions

Extend existing models to support personalization and interventions:
- `user_profiles` (extend)
  - `weekly_rhythm` – float[168] (0–1) stress propensity by hour-of-week
  - `preferred_strategies` – JSONB (strategy → weight, last_success)
  - `recent_struggles` – JSONB (top recurring tag clusters)
- `interventions` (new)
  - planned/sent interventions: `id`, `user_id`, `type` (breathing/reflection), `scheduled_time`, `created_at`, `delivered_at`, `result` (accepted/skipped/ignored), `metadata`
- `token_usage` (done) for monthly aggregation and limits

---

## 5) API Endpoints (Phased)

- Usage (DONE)
  - `GET /user/limitations` – monthly usage vs 250k limit
- Profile
  - `GET /profile/summary` – small card: trending tags, recent struggles, suggestions
  - `POST /profile/feedback` – accept/skip suggestion feedback
- Interventions
  - `GET /interventions/next` – N suggested upcoming interventions (client schedules locally)
  - `POST /interventions/event` – log shown/accepted/skipped
- Chat
  - `POST /api/v1/chat` – strict JSON output schema (reply, tags, confidence, suggestion)

---

## 6) Prompt & Output Contracts

Use strict, validated JSON outputs to keep UI stable.
- System: therapist role, empathy, boundaries, safety
- Context: user_profile, recent_tags, effective_strategies, schedule_window
- Output schema example:

```
{
  "reply": "...",
  "tags": ["work_stress", "anxious"],
  "confidence": 0.82,
  "followups": ["Try a 2‑min breathing exercise?"],
  "safety": {"crisis": false},
  "insights": ["Recurring stress Tue evenings"],
  "suggestion": {"type": "breathing", "pattern": "box", "duration_min": 2}
}
```

Fail‑closed: if invalid schema, return safe canned reply; log and track rate.

---

## 7) Proactive Notifications Flow

Consent-based flow:
1) Nightly job updates `weekly_rhythm`; refreshes profile summary
2) API returns next N suggested slots/content (start with client-side scheduling)
3) Flutter schedules local notifications; captures feedback (accepted/skipped)

UX principles:
- Subtle surfaces, frequency caps, quiet hours
- Clear opt‑in/out and privacy controls

---

## 8) AWS Deployment Plan

### Phase A – EC2 + RDS (Baseline)
- EC2: Uvicorn behind NGINX (Docker); health checks + autoscaling group optional
- RDS PostgreSQL: production DB; daily snapshots; minor version auto‑upgrade window
- ElastiCache Redis: caching/events for later features
- CloudWatch: logs, dashboards, and alarms (p95 latency, error rate, CPU, DB connections)
- Secrets Manager/Parameter Store: OpenAI key, DB creds, JWT secret
- VPC: ALB public → EC2 private; RDS in private subnets; strict SG rules

### Phase B – Serverless Helpers
- EventBridge scheduled Lambdas: nightly profile refresh; weekly summary generation
- SQS: background jobs (rebuild profiles, backfills)
- Step Functions: training/evaluation workflows

### Phase C – Model Hosting (when needed)
- TorchServe on EC2 (GPU optional) or SageMaker endpoints
- Model artifacts in S3; CI/CD deploys via GitHub Actions

### IaC & CI/CD
- Terraform (or CDK) for reproducible infra
- GitHub Actions: test → build → push → deploy; Alembic migrations on deploy

---

## 9) Observability, SLOs, and Cost Control

- Observability
  - RED metrics: request rate, errors, duration; p50/p95 latency dashboards
  - Tracing: OpenTelemetry in API critical paths (chat, tagging)
  - App logs: structured JSON; correlation IDs; user PII redacted
- SLOs
  - Chat endpoint: p95 < 1.5s (non-streaming), > 99.5% availability
  - Tagging pipeline: p95 < 1.2s
- Cost
  - Token budgets per user/month (already enforced)
  - Prefer smaller LLMs and short prompts; cache recent summaries
  - Shift “checks” to PyTorch where possible (cheap inference)

---

## 10) Security & Privacy

- Data minimization: store only what’s necessary; split PII from analytics
- Consent flows: proactive notifications opt‑in with clear language
- Access controls: per‑user isolation; least privilege on AWS (IAM + SG)
- Crypto: TLS in transit; encrypted RDS snapshots; at‑rest encryption
- User rights: export/delete‑my‑data endpoints and admin tooling
- Safety: crisis detection guardrails; escalation playbook with local resources

---

## 11) PyTorch Learning Path (Inside This Project)

1) Data export: anonymized messages + tags to Parquet (S3); add small exploration notebooks
2) Tag Consistency classifier:
   - Baseline rules → small CNN/DistilBERT; train/evaluate; export TorchScript
   - Integrate at `infrastructure/tagging/services/tag_consistency_torch.py`
3) Coping Recommender v0:
   - Start rule‑based + weighted history; later a learned ranker
4) Temporal Stress predictor:
   - LSTM/TCN; write predictions to `weekly_rhythm` for scheduling
5) Measure impact: F1 for tags, acceptance rate, tokens saved, latency

Serving: start in‑process (CPU, TorchScript). Move to TorchServe/SageMaker if needed.

---

## 12) Roadmap & Deliverables

### Short term (1–2 weeks)
- Feature folderization (usage, tagging, chat, records, breathing)
- `interventions` table + `RecommendationService` skeleton
- Extend `user_profiles` for `weekly_rhythm` and `preferred_strategies`
- Home “Today’s suggestion” card (static placeholder)

### Medium term (3–6 weeks)
- PyTorch Tag Consistency (TorchScript) in tagging flow
- Notification planning (server) + local scheduling (client)
- Weekly Review endpoint + UI screen

### Long term (6–12 weeks)
- Recommender + Temporal predictor models
- Vector DB for similar experiences (FAISS/Qdrant)
- TorchServe/SageMaker; A/B tests for interventions and prompts

---

## 13) Example Folder Structures

### Backend
```
src/
  domain/
    usage/interfaces.py
    chat/interfaces.py
    tagging/interfaces.py
  application/
    chat/use_cases.py
    tagging/services.py
    usage/use_cases.py
  infrastructure/
    usage/repositories/sqlalchemy_token_usage_repository.py
    tagging/services/openai_tagging_service.py
    tagging/services/tag_consistency_torch.py
    database/models.py
  presentation/
    api/routers/
      chat.py
      usage.py
      records.py
      breathing.py
```

### Flutter
```
lib/
  features/
    usage/
      data/api.dart
      presentation/widgets/token_usage.dart
    chat/
      data/api.dart
      presentation/screens/chat_screen.dart
    interventions/
      presentation/widgets/suggestion_card.dart
  shared/
    theme/
    widgets/
```

---

## 14) Definition of Done (DoD)
- APIs return validated JSON; LLM failures fail‑closed with safe responses
- Token usage budget enforced and observable (dashboards + alerts)
- Feature folders in both repos; imports updated; tests passing
- Nightly job(s) scheduled; privacy consent captured; data export/delete working
- Basic PyTorch model (consistency) integrated and measured for impact

This plan keeps the system modular, adds real personalization with PyTorch, retains LLM strengths, and sets you up for a smooth AWS deployment. It’s also ideal for learning PyTorch with real user impact.
