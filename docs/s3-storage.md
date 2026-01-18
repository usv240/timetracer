# S3 Storage

Store and retrieve cassettes from AWS S3 or S3-compatible storage.

## Installation

```bash
pip install timetracer[s3]
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
timetracer s3 upload ./cassettes/POST__checkout__a91c.json -b my-bucket

# Upload directory
timetracer s3 upload ./cassettes/ -b my-bucket
```

### Download from S3

```bash
timetracer s3 download 2026-01-15/POST__checkout__a91c.json -b my-bucket -o ./local.json
```

### List cassettes

```bash
timetracer s3 list -b my-bucket -n 50
```

### Sync cassettes

```bash
# Upload all local cassettes to S3
timetracer s3 sync up -d ./cassettes -b my-bucket

# Download all S3 cassettes to local
timetracer s3 sync down -d ./cassettes -b my-bucket
```

## Python API

```python
from timetracer.storage import S3Store, S3Config

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

## CI/CD Integration

### ArgoWorkflows

Store cassettes as workflow artifacts for debugging production issues:

```yaml
# argo-workflow.yaml
apiVersion: argoproj.io/v1alpha1
kind: Workflow
spec:
  templates:
    - name: api-task
      container:
        image: your-api:latest
        env:
          - name: TIMETRACER_MODE
            value: record
          - name: TIMETRACER_S3_BUCKET
            value: cassettes-bucket
          - name: TIMETRACER_S3_PREFIX
            value: workflows/{{workflow.name}}
```

When a task fails:
1. Download the cassette from S3
2. Replay locally with dependencies mocked
3. Debug without needing production access

### GitHub Actions

```yaml
- name: Upload cassettes on failure
  if: failure()
  run: timetracer s3 upload ./cassettes -b ${{ secrets.CASSETTE_BUCKET }}
```

### Generic CI

Any CI that supports S3 artifacts can use Timetracer:

```bash
# After running tests or on failure
TIMETRACER_S3_BUCKET=my-bucket timetracer s3 sync up -d ./cassettes
```

