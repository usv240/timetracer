# Timetracer Security Guide

Best practices for secure usage of Timetracer cassettes.

## Default Redaction

Timetracer automatically redacts sensitive data to prevent accidental exposure.

### Sensitive Headers (Always Removed)

These headers are **never** stored in cassettes:

**Authentication:**
- `authorization`
- `x-api-key`, `api-key`, `apikey`
- `x-auth-token`, `x-access-token`, `x-refresh-token`
- `x-session-token`

**Security Tokens:**
- `x-csrf-token`, `x-xsrf-token`

**Session/Cookies:**
- `cookie`, `set-cookie`

**Proxy:**
- `proxy-authorization`, `www-authenticate`

### Sensitive Body Keys (Masked)

Values for keys containing these patterns are replaced with `[REDACTED]`:

**Authentication & Security:**
- `password`, `passwd`, `pwd`, `secret`
- `token`, `api_key`, `apikey`, `access_token`, `refresh_token`
- `private_key`, `secret_key`, `signing_key`, `encryption_key`
- `csrf`, `xsrf`, `otp`, `mfa`, `pin`

**Personal Information (PII):**
- `ssn`, `social_security`, `passport`, `driver_license`
- `phone`, `mobile`, `email`, `email_address`
- `date_of_birth`, `dob`, `address`, `zip_code`

**Financial (PCI-DSS Compliance):**
- `credit_card`, `card_number`, `cvv`, `cvc`
- `bank_account`, `account_number`, `routing_number`
- `iban`, `swift`, `expiry`, `cardholder`

**Healthcare (HIPAA Compliance):**
- `patient_id`, `medical_record`, `diagnosis`
- `insurance_id`, `policy_number`, `provider_id`

### PII Pattern Detection

Timetracer also detects and redacts PII patterns in string values:

| Pattern | Example | Redacted As |
|---------|---------|-------------|
| Email | `user@example.com` | `[REDACTED:EMAIL]` |
| Phone | `555-123-4567` | `[REDACTED:PHONE]` |
| SSN | `123-45-6789` | `[REDACTED:SSN]` |
| Credit Card (Luhn validated) | `4111-1111-1111-1111` | `[REDACTED:CREDIT_CARD]` |
| IPv4 | `192.168.1.1` | `[REDACTED:IP]` |
| IPv6 | `2001:0db8:...` | `[REDACTED:IP]` |
| JWT | `eyJhbGc...` | `[REDACTED]` |

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
from timetracer.config import TraceConfig
from timetracer.constants import CapturePolicy

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
timetracer show ./cassettes/path/to/cassette.json
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
from timetracer.constants import Redaction

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
