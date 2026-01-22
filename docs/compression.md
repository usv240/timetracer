# Cassette Compression

Timetracer supports gzip compression for cassettes, reducing storage by **60-95%**.

## Why Compression?

Cassette files can grow large, especially in test suites with many API calls. Without compression:
- A typical cassette: 40-50 KB
- 100 cassettes: ~4-5 MB
- 1000 cassettes: ~40-50 MB

With gzip compression:
- Same cassettes: **2-5 KB each**
- 100 cassettes: ~200-500 KB
- 1000 cassettes: ~2-5 MB

## Quick Start

### Via Environment Variable

```bash
# Enable gzip compression
export TIMETRACER_COMPRESSION=gzip

# Record with compression
TIMETRACER_MODE=record uvicorn app:app
```

### Via Code

```python
from timetracer import TraceConfig, CompressionType
from timetracer.integrations.fastapi import TimeTracerMiddleware

config = TraceConfig(
    mode="record",
    compression=CompressionType.GZIP,
)

app.add_middleware(TimeTracerMiddleware, config=config)
```

## File Extensions

| Compression | Extension | Example |
|-------------|-----------|---------|
| None (default) | `.json` | `GET__users__abc123.json` |
| Gzip | `.json.gz` | `GET__users__abc123.json.gz` |

## Auto-Detection on Read

Timetracer automatically detects compression when reading cassettes:

```python
from timetracer.cassette.io import read_cassette

# Both work automatically
cassette1 = read_cassette("recording.json")      # Uncompressed
cassette2 = read_cassette("recording.json.gz")   # Gzip compressed
```

No configuration needed for reading—the file extension tells Timetracer which format to use.

## Configuration Reference

| Setting | Environment Variable | Values | Default |
|---------|---------------------|--------|---------|
| Compression | `TIMETRACER_COMPRESSION` | `none`, `gzip` | `none` |

## pytest Integration

Compressed cassettes work seamlessly with pytest fixtures:

```python
def test_api_endpoint(timetracer_replay):
    # Automatically detects .json.gz
    with timetracer_replay("my_test.json.gz"):
        response = client.get("/api/users")
        assert response.status_code == 200
```

Record compressed cassettes:

```python
def test_record_compressed(timetracer_record):
    # Configure compression globally
    import os
    os.environ["TIMETRACER_COMPRESSION"] = "gzip"
    
    with timetracer_record("new_cassette.json.gz") as session:
        response = client.get("/api/data")
```

## CLI Support

View compressed cassettes:

```bash
# Show works with compressed files
timetracer show cassettes/GET__users.json.gz

# Dashboard includes compressed cassettes
timetracer dashboard --dir ./cassettes
```

## Size Comparison Example

Run the comparison script in `examples/compression_example/`:

```bash
cd examples/compression_example
python compare_sizes.py
```

Output:
```
============================================================
Cassette Compression Size Comparison
============================================================

Sample cassette with 50 user records:

  [JSON] Uncompressed (.json):    44,662 bytes
  [GZIP] Compressed (.json.gz):    1,915 bytes

  SAVED: 42,747 bytes (95.7%)
```

## When to Use Compression

**Recommended:**
- Large test suites (100+ cassettes)
- CI/CD pipelines (faster artifact upload/download)
- Projects committed to version control
- Cassettes with large response bodies

**Not necessary:**
- Development/debugging (readability matters)
- Small projects with few cassettes
- When disk space isn't a concern

## Mixing Compressed and Uncompressed

You can have both `.json` and `.json.gz` files in the same directory. Timetracer handles both transparently.

```
cassettes/
├── 2026-01-22/
│   ├── GET__users__abc.json      # Uncompressed
│   ├── POST__orders__def.json.gz  # Compressed
│   └── GET__products__ghi.json.gz # Compressed
```

## Compression Levels

Currently, Timetracer uses Python's default gzip compression level (9, maximum compression). Future versions may allow configuring this.

## Troubleshooting

### Cannot open compressed cassette

Ensure the file has the correct `.gz` extension:
```bash
# Check if it's actually gzip
file cassettes/recording.json.gz
# Should show: gzip compressed data
```

### Large compressed files

If compressed files are still large, check for:
- Binary data in response bodies (doesn't compress well)
- Already-compressed content (images, etc.)
- Very large response bodies (consider `max_body_kb` setting)
