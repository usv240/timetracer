# Compression Example

This example demonstrates the cassette compression feature in Timetracer.

## Why Compression?

Cassette files can grow large, especially in test suites with many API calls. Gzip compression typically reduces cassette size by **60-80%**, saving disk space and making cassettes faster to transfer.

## Quick Start

### 1. Enable Compression via Environment Variable

```bash
# Enable gzip compression
export TIMETRACER_COMPRESSION=gzip

# Start your app
TIMETRACER_MODE=record uvicorn app:app
```

### 2. Enable Compression via Code

```python
from timetracer import TraceConfig, CompressionType
from timetracer.integrations.fastapi import TimeTracerMiddleware

config = TraceConfig(
    mode="record",
    compression=CompressionType.GZIP,  # Enable gzip compression
)

app.add_middleware(TimeTracerMiddleware, config=config)
```

## File Extensions

- **No compression**: `GET__users__abc123.json`
- **Gzip compression**: `GET__users__abc123.json.gz`

Timetracer auto-detects the compression format when reading cassettes.

## Running the Example

### Record with Compression

```bash
cd examples/compression_example

# Record with gzip compression
TIMETRACER_MODE=record TIMETRACER_COMPRESSION=gzip python app.py
```

This creates compressed cassettes in `./cassettes/`.

### Compare Sizes

```bash
# Run the comparison script
python compare_sizes.py
```

This shows the size difference between compressed and uncompressed cassettes.

## pytest Integration

Use compression in your tests:

```python
def test_with_compression(timetracer_replay):
    # Timetracer auto-detects .json.gz files
    with timetracer_replay("my_cassette.json.gz"):
        response = client.get("/api/users")
        assert response.status_code == 200
```

## Configuration Options

| Variable | Values | Default |
|----------|--------|---------|
| `TIMETRACER_COMPRESSION` | `none`, `gzip` | `none` |

## Benefits

1. **Smaller storage**: 60-80% size reduction
2. **Faster CI/CD**: Less data to upload/download
3. **Safe to commit**: Compressed cassettes are smaller in git
4. **Zero config read**: Auto-detection means no config needed to read
