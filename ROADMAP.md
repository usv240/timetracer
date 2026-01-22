# Timetracer Roadmap

Based on user feedback from r/FastAPI, r/Django, and GitHub issues.

---

## Completed Milestones

### ✅ v1.5.0
- **Cassette Compression**: Gzip compression support (60-95% size reduction).
- **MongoDB/Motor Plugin**: Async MongoDB support (find, insert, update, delete).

### ✅ v1.4.0
- **Django Integration**: Full middleware support (Sync/Async).
- **pytest Plugin**: Zero-config fixtures (`timetracer_replay`, etc).
- **Documentation**: Unified guides for all frameworks.

### ✅ v1.3.0
- **aiohttp Plugin**: Fully supported.
- **S3 Integration**: Remote cassette storage.
- **CI/CD Guides**: ArgoWorkflows, GitHub Actions.

---

## Priority 1: Async Database Support

Modern Python frameworks (FastAPI, Litestar, Django 4+) heavily use async database drivers. We need to support them natively.

| Driver | Status | Notes |
|--------|--------|-------|
| **SQLAlchemy (Sync)** | ✅ Done | Reference implementation |
| **SQLAlchemy (Async)** | 🚧 In Progress | asyncpg/aiomysql via SQLA |
| **asyncpg** | Planned | Native PostgreSQL async |
| **Motor** | ✅ Done | MongoDB async |
| **Tortoise ORM** | Planned | Popular async ORM |

---

## Priority 2: Advanced Data Handling

As adoption grows, users need more control over sensitive data and complex request types.

### GraphQL Support
- Parse GraphQL queries (currently treated as generic POST requests)
- Match by operation name/variables
- Schema-aware redaction

### Cassette Encryption
- Encrypt cassettes at rest (AES-GCM)
- Key management via environment variables
- Safe to commit encrypted cassettes to public repos

### Request Diffing & Comparison
- `timetracer diff` command
- Compare a failed replay against the recorded baseline
- Highlight why a match failed (header mismatch? body drift?)

---

## Priority 3: Developer Experience

### VS Code Extension
- "Record/Replay" buttons directly in the editor
- Cassette explorer in the side panel
- Click-to-open cassette JSON

### CLI Enhancements
- `timetracer watch`: Live tail of new cassettes
- `timetracer clean`: Smart cleanup of unused/expired cassettes
- `timetracer validate`: Schema validation

---

## Future Frameworks

| Framework | Status | Notes |
|-----------|--------|-------|
| **FastAPI** | ✅ Done | |
| **Flask** | ✅ Done | |
| **Django** | ✅ Done | |
| **Litestar** | Planned | Growing popularity |
| **Starlette** | Planned | Native integration |

---

## Contribution Opportunities

We love contributions! Here are some areas where you can help:

**Good first issues:**
- Add more PII patterns to `detect_pii()`
- Improve CLI help text and error messages
- Add specific tech stack examples (e.g., "FastAPI + Celery")

**Medium difficulty:**
- Add a new database plugin (e.g., PyMongo)
- Improve the Dashboard UI (HTML/JS)

**Larger projects:**
- GraphQL parser integration
- VS Code Extension

---

## Vision

Key differentiators of Timetracer vs VCR.py/Betamax:
1. **Full Stack Capture**: HTTP + DB + Redis in one cassette.
2. **Production-First**: Designed as middleware for live apps, not just test decorators.
3. **Visualization**: Built-in dashboard and timeline view.
4. **Cloud Native**: S3 storage and Kubernetes operational modes.
