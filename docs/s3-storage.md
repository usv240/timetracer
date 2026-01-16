# S3 Storage

Store and retrieve cassettes from AWS S3 or S3-compatible storage.

## Installation

```bash
pip install timetrace[s3]
```

## Configuration

### Environment Variables

| Variable | Description |
|----------|-------------|
| `TIMETRACER_S3_BUCKET` | S3 bucket name (required) |
| `TIMETRACER_S3_PREFIX` | Key prefix (default: `cassettes`) |
| `TIMETRACER_S3_REGION` | AWS region |
| `TIMETRACER_S3_ENDPOINT` | Custom endpoint (MinIO, LocalStack) |
| `AWS_ACCESS_KEY_ID` | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key |

## CLI Usage

### Upload cassettes to S3

```bash
# Upload single file
timetrace s3 upload ./cassettes/POST__checkout__a91c.json -b my-bucket

# Upload directory
timetrace s3 upload ./cassettes/ -b my-bucket
```

### Download from S3

```bash
timetrace s3 download 2026-01-15/POST__checkout__a91c.json -b my-bucket -o ./local.json
```

### List cassettes

```bash
timetrace s3 list -b my-bucket -n 50
```

### Sync cassettes

```bash
# Upload all local cassettes to S3
timetrace s3 sync up -d ./cassettes -b my-bucket

# Download all S3 cassettes to local
timetrace s3 sync down -d ./cassettes -b my-bucket
```

## Python API

```python
from timetrace.storage import S3Store, S3Config

# Configure
config = S3Config(
    bucket="my-cassettes",
    prefix="api-traces",
    region="us-east-1",
)
store = S3Store(config)

# Upload
store.upload("./cassettes/POST__checkout.json")

# Download
store.download("2026-01-15/POST__checkout.json", "./local.json")

# List
for key in store.list(limit=100):
    print(key)

# Read directly
data = store.read("2026-01-15/POST__checkout.json")

# Write directly
store.write("custom/key.json", cassette_data)

# Sync
store.sync_upload("./cassettes/")
store.sync_download("./local_cassettes/")
```

## S3-Compatible Storage

For MinIO, LocalStack, or other S3-compatible storage:

```python
config = S3Config(
    bucket="my-bucket",
    endpoint_url="http://localhost:9000",  # MinIO
    access_key="minioadmin",
    secret_key="minioadmin",
)
```

Or via environment:
```bash
export TIMETRACER_S3_ENDPOINT=http://localhost:9000
export AWS_ACCESS_KEY_ID=minioadmin
export AWS_SECRET_ACCESS_KEY=minioadmin
```
