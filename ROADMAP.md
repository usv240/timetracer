# Timetracer Roadmap

Based on user feedback from r/FastAPI and feature requests.

---

## Completed in v1.3.0

- aiohttp plugin (full support)
- S3 integration documentation
- CI/CD integration guide (ArgoWorkflows, GitHub Actions)
- FastAPI + aiohttp example project

---

## Priority 1: Additional HTTP Client Plugins

| Client | Popularity | Difficulty | Status |
|--------|------------|------------|--------|
| httpx | Very High | Done | Complete |
| requests | Very High | Done | Complete |
| aiohttp | High | Done | Complete |
| urllib3 | Medium | Medium | Planned |

---

## Priority 2: Async Database Plugins

| Database | Current Support | Notes |
|----------|-----------------|-------|
| SQLAlchemy | Complete | Sync + some async |
| asyncpg | Planned | Native PostgreSQL async |
| aiomysql | Planned | MySQL async |
| motor | Planned | MongoDB async |
| Tortoise ORM | Planned | Popular async ORM |

---

## Priority 3: Async Cache Support

| Service | Current Support | Notes |
|---------|-----------------|-------|
| Redis (sync) | Complete | redis-py |
| Redis (async) | Planned | redis.asyncio |
| Memcached | Planned | pymemcache |

---

## Priority 4: Framework Integrations

| Framework | Current Support | Notes |
|-----------|-----------------|-------|
| FastAPI | Complete | Middleware + auto_setup |
| Flask | Complete | Middleware |
| Starlette | Complete | Via FastAPI |
| Django | Planned | High demand |
| Litestar | Planned | Growing popularity |

---

## Priority 5: Testing Integrations

### pytest-timetracer

```python
@pytest.mark.cassette("checkout_flow.json")
def test_checkout():
    response = client.post("/checkout")
    assert response.status_code == 200
```

Features:
- Auto-generate cassettes from first run
- Compare responses between runs
- Cassette directory per test module

---

## Priority 6: Developer Experience

### CLI Improvements
- `timetracer watch` - Live tail of new cassettes
- `timetracer compare` - Better diff output
- `timetracer clean` - Remove old/duplicate cassettes
- `timetracer validate` - Check cassette schema

### Dashboard Improvements
- Real-time WebSocket updates
- Cassette comparison view
- Request grouping by session/trace ID

---

## Priority 7: Advanced Features

### GraphQL Support
- Parse GraphQL queries
- Match by operation name, not just URL
- Variable extraction and comparison

### Request Diffing
```bash
timetracer diff --a baseline.json --b current.json --format html
```
- Side-by-side response comparison
- Highlight changes in body, headers, timing

### Cassette Encryption
- Encrypt cassettes at rest
- Key management via environment or vault

---

## Release Plan

### v1.4.0
- Django middleware
- asyncpg plugin
- Request diffing improvements

### v1.5.0
- GraphQL support
- Cassette encryption

### v2.0.0
- Full pytest integration
- VS Code extension

---

## Contribution Opportunities

**Good first issues:**
- Add more PII patterns to redaction
- Improve CLI help text
- Add more cassette validation

**Medium difficulty:**
- pytest fixture
- Django middleware

**Larger projects:**
- GraphQL parser
- VS Code extension

---

## Notes

Key differentiators of Timetracer vs VCR.py/Betamax:
1. Multi-dependency capture (HTTP + DB + Redis in one cassette)
2. Production-first (middleware, not just test decorators)
3. Built-in dashboard and visualization
4. S3 cloud storage
5. Advanced redaction for PII
