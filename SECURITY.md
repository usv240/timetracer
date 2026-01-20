# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 1.0.x   | Yes       |
| 0.x     | No        |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to: [ujwalv098@gmail.com]

You should receive a response within 48 hours. If for some reason you do not, please follow up via email to ensure we received your original message.

Please include the following information:
- Type of issue (e.g., sensitive data exposure, injection, etc.)
- Full paths of source file(s) related to the issue
- Location of the affected source code (tag/branch/commit or direct URL)
- Step-by-step instructions to reproduce
- Proof-of-concept or exploit code (if possible)
- Impact of the issue

## Security Measures in Timetracer

### Sensitive Data Handling

Timetracer implements multiple layers of protection:

1. **Header Redaction (Default)**
   - `Authorization` - Always removed
   - `Cookie` - Always removed
   - `Set-Cookie` - Always removed
   - `X-API-Key` - Always removed

2. **Body Redaction (Default)**
   - `password` fields - Masked
   - `token` fields - Masked
   - `api_key` fields - Masked
   - `secret` fields - Masked
   - JWT tokens - Detected and masked

3. **Capture Policies**
   - Bodies captured only on errors by default
   - Size limits enforced (64KB default)
   - Truncation for large payloads

### Best Practices

When using Timetracer:

1. **Never commit cassettes** with production data to version control
2. **Add `cassettes/` to `.gitignore`**
3. **Review cassettes** before sharing
4. **Use `errors_only=True`** in production-like environments
5. **Configure additional redaction** for your domain-specific sensitive keys

### Configuration

```python
from timetracer.config import TraceConfig

config = TraceConfig(
    # Only record on errors
    errors_only=True,
    # Don't store bodies by default
    store_request_body="never",
    store_response_body="on_error",
)
```

## Disclosure Policy

When we receive a security bug report, we will:

1. Confirm the problem and determine affected versions
2. Audit code to find similar problems
3. Prepare fixes for all supported versions
4. Release patched versions
5. Announce the vulnerability (after patch is available)
