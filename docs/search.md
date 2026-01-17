# Cassette Search

Search and index cassettes for fast retrieval.

## CLI Usage

### Search cassettes

```bash
# Search by endpoint
timetracer search --endpoint /checkout

# Search by HTTP method
timetracer search --method POST

# Search by status code
timetracer search --status 500

# Search errors only
timetracer search --errors

# Combine filters
timetracer search --method POST --endpoint /api --errors --limit 50

# Output as JSON
timetracer search --endpoint /checkout --json
```

### Build index

For faster searching on large cassette directories:

```bash
timetracer index --dir ./cassettes --out ./cassettes/index.json
```

## Python API

```python
from timetracer.catalog import search_cassettes, build_index, save_index

# Search cassettes
results = search_cassettes(
    cassette_dir="./cassettes",
    method="POST",
    endpoint="/checkout",
    errors_only=True,
    limit=20,
)

for entry in results:
    print(f"{entry.method} {entry.endpoint} - {entry.status}")

# Build and save index
index = build_index("./cassettes")
save_index(index, "./cassettes/index.json")

# Access index entries
for entry in index.entries[:10]:
    print(f"{entry.recorded_at}: {entry.method} {entry.endpoint}")
```

## Search Filters

| Filter | Description |
|--------|-------------|
| `method` | HTTP method (GET, POST, etc.) |
| `endpoint` | Path partial match |
| `status_min` | Minimum status code |
| `status_max` | Maximum status code |
| `errors_only` | Only 4xx/5xx responses |
| `service` | Service name |
| `env` | Environment |
| `date_from` | Recorded after date |
| `date_to` | Recorded before date |
| `limit` | Max results |

## CassetteEntry Fields

Each search result contains:

| Field | Description |
|-------|-------------|
| `path` | Relative path to cassette |
| `method` | HTTP method |
| `endpoint` | Request path |
| `status` | Response status code |
| `duration_ms` | Request duration |
| `recorded_at` | ISO timestamp |
| `service` | Service name |
| `event_count` | Number of dependency events |
| `has_errors` | True if status >= 400 |
