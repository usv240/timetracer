# Full Integration Example

A comprehensive example and test suite that exercises ALL Timetrace features.

## Files

- `app.py` - Full FastAPI application with 20+ endpoints
- `test_edge_cases.py` - Edge case test covering all scenarios

## Run Edge Case Tests

```bash
cd examples/full_integration
python test_edge_cases.py
```

## Tests Covered

| Category | Tests |
|----------|-------|
| Error Responses | 404, 500 |
| Body Capture | always, never, on_error |
| Large Bodies | Size capping |
| Replay | Record/replay cycle |
| Empty Response | 204 No Content |
| Multiple Requests | Sequential recording |
| Sampling | 0%, 50% rates |

## Run the App

```bash
# Record mode
TIMETRACE_MODE=record python -m uvicorn app:app

# Make requests
curl http://localhost:8000/products
curl -X POST "http://localhost:8000/products?name=Test&price=9.99"
curl http://localhost:8000/external/json
```
