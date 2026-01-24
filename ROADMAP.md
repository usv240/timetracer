# Timetracer Roadmap

This roadmap is based on user feedback from r/FastAPI, r/Django, and GitHub issues.

## Completed Milestones

### v1.6.0
- **PyMongo Plugin**: Synchronous MongoDB support (find, insert, update, delete, aggregation)
- **Starlette Integration**: Lightweight ASGI framework support

### v1.5.0
- **Cassette Compression**: Gzip compression support (60-95% size reduction)
- **Motor Plugin**: Async MongoDB support (find, insert, update, delete)

### v1.4.0
- **Django Integration**: Full middleware support (sync/async views)
- **pytest Plugin**: Zero-config fixtures (timetracer_replay, timetracer_record, timetracer_auto)
- **Documentation**: Unified guides for all frameworks

### v1.3.0
- **aiohttp Plugin**: Full async HTTP client support
- **S3 Integration**: Remote cassette storage
- **CI/CD Guides**: ArgoWorkflows and GitHub Actions integration

## Priority 1: Async Database Support

Modern Python frameworks (FastAPI, Litestar, Django 4+) heavily use async database drivers. Native support for these drivers is a priority.

| Driver | Status | Notes |
|--------|--------|-------|
| SQLAlchemy (Sync) | Done | Reference implementation |
| SQLAlchemy (Async) | In Progress | asyncpg/aiomysql via SQLA |
| asyncpg | Planned | Native PostgreSQL async |
| Motor | Done | MongoDB async |
| PyMongo | Done | MongoDB sync |
| Tortoise ORM | Planned | Popular async ORM |

## Priority 2: Advanced Data Handling

As adoption grows, users need more control over sensitive data and complex request types.

### GraphQL Support
- Parse GraphQL queries (currently treated as generic POST requests)
- Match by operation name and variables
- Schema-aware redaction

### Cassette Encryption
- Encrypt cassettes at rest (AES-GCM)
- Key management via environment variables
- Safe to commit encrypted cassettes to public repositories

### Request Diffing & Comparison
- Enhanced `timetracer diff` command
- Compare failed replay against recorded baseline
- Highlight match failures (header mismatch, body drift, etc.)

## Priority 3: Developer Experience

### VS Code Extension
- Record/Replay buttons in editor
- Cassette explorer in side panel
- Click to open cassette JSON

### CLI Enhancements
- `timetracer watch`: Live tail of new cassettes
- `timetracer clean`: Smart cleanup of unused/expired cassettes
- `timetracer validate`: Schema validation

## Framework Support

| Framework | Status | Notes |
|-----------|--------|-------|
| FastAPI | Done | Full ASGI support |
| Starlette | Done | ASGI foundation |
| Flask | Done | WSGI support |
| Django | Done | Sync/async views |
| Litestar | Planned | Growing popularity |

## Contribution Opportunities

We welcome contributions in these areas:

**Good First Issues:**
- Add more PII patterns to `detect_pii()`
- Improve CLI help text and error messages
- Add specific tech stack examples (e.g., "FastAPI + Celery")

**Medium Difficulty:**
- Add new database plugins
- Improve Dashboard UI (HTML/JS)
- Add framework integrations

**Larger Projects:**
- GraphQL parser integration
- VS Code Extension
- Advanced cassette encryption

## Vision

Key differentiators of Timetracer vs VCR.py/Betamax:

1. **Full Stack Capture**: HTTP + Database + Redis in a single cassette
2. **Production-First**: Designed as middleware for live applications, not just test decorators
3. **Visualization**: Built-in dashboard and timeline views
4. **Cloud Native**: S3 storage and Kubernetes operational modes

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to this roadmap.
