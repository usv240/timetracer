# Timetrace Security Guide

Best practices for secure usage of Timetrace cassettes.

## Default Redaction

Timetrace automatically redacts sensitive data to prevent accidental exposure.

### Sensitive Headers (Always Removed)

These headers are **never** stored in cassettes:

- `authorization`
- `cookie`
- `set-cookie`
- `x-api-key`
- `x-auth-token`
- `x-access-token`

### Sensitive Body Keys (Masked)

Values for these keys are replaced with `[REDACTED]`:

- `password`
- `secret`
- `token`
- `api_key` / `apikey`
- `access_token`
- `refresh_token`
- `private_key`
- `credit_card`
- `ssn`

## Allowed Headers

For outbound HTTP calls, only these headers are captured:

- `content-type`
- `content-length`
- `accept`
- `user-agent`
- `x-request-id`
- `x-correlation-id`

## Configuration Options

### Body Capture Policies

Control when body data is stored:

```python
from timetrace.config import TraceConfig
from timetrace.constants import CapturePolicy

config = TraceConfig(
    # Only store bodies on errors
    store_request_body=CapturePolicy.ON_ERROR,
    store_response_body=CapturePolicy.ON_ERROR,
    
    # Or never store bodies (hash only)
    # store_request_body=CapturePolicy.NEVER,
    # store_response_body=CapturePolicy.NEVER,
)
```

### Size Limits

```python
config = TraceConfig(
    max_body_kb=64,  # Truncate bodies larger than 64KB
)
```

### Exclude Sensitive Endpoints

```python
config = TraceConfig(
    exclude_paths=[
        "/health",
        "/metrics",
        "/auth/login",
        "/auth/token",
        "/admin/*",
    ],
)
```

## Best Practices

### 1. Review Before Committing

Always review cassettes before committing to version control:

```bash
timetrace show ./cassettes/path/to/cassette.json
```

### 2. Use `.gitignore` for Local Cassettes

```gitignore
# Don't commit local test cassettes
cassettes/local/
cassettes/*.json

# Only commit curated test fixtures
!cassettes/fixtures/
```

### 3. Production Safety

**Never enable recording in production** with sensitive data:

```python
import os

config = TraceConfig(
    # Only record in development/staging
    mode="record" if os.environ.get("ENV") != "production" else "off",
    errors_only=True,  # Minimize data captured
)
```

### 4. PII Considerations

For GDPR/CCPA compliance:
- Use `errors_only=True` to minimize data
- Add custom redaction for user-specific fields
- Set short retention policies for cassettes
- Consider encryption at rest (v2.0+)

### 5. API Keys and Tokens

External API keys are automatically redacted in headers, but:
- Check body data for embedded tokens
- Use `CapturePolicy.NEVER` for sensitive endpoints
- Review cassettes for leaked credentials

## Custom Redaction

Extend the default redaction rules:

```python
from timetrace.constants import Redaction

# Add custom sensitive keys (for body redaction)
CUSTOM_SENSITIVE_KEYS = Redaction.SENSITIVE_BODY_KEYS | {
    "social_security",
    "bank_account",
    "date_of_birth",
}
```

## Cassette Storage Security

### Local Storage
- Cassettes are stored as plain JSON files
- Use filesystem permissions to restrict access
- Consider encrypting the cassette directory

### Cloud Storage (v2.0+)
- Use S3/GCS bucket policies
- Enable encryption at rest
- Use IAM roles for access control

## Audit Trail

Cassettes include metadata for auditing:

```json
{
  "session": {
    "id": "unique-session-id",
    "recorded_at": "2026-01-15T14:30:00Z",
    "service": "my-api",
    "env": "staging"
  },
  "policies": {
    "redaction_mode": "default",
    "redaction_rules": ["authorization", "cookie"]
  }
}
```
