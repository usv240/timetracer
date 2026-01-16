# Contributing to Timetracer

Thank you for your interest in contributing to Timetracer! This document provides guidelines for contributing.

## Getting Started

### 1. Fork and Clone

```bash
git clone https://github.com/usv240/timetracer.git
cd timetracer
```

### 2. Install in Development Mode

```bash
pip install -e ".[dev]"
```

This installs all dependencies including:
- pytest (testing)
- ruff (linting)
- uvicorn (dev server)
- fakeredis (Redis testing)

### 3. Verify Setup

```bash
# Check installation
python -c "import timetracer; print(timetracer.__version__)"
```

## Development Workflow

### Running Tests

```bash
# Run all unit tests
pytest tests/ -v

# Run integration tests
python examples/fastapi_httpx/test_complete.py

# Run edge case tests
python examples/full_integration/test_edge_cases.py

# Run real end-to-end tests (starts actual server)
python examples/full_integration/test_e2e_real.py
```

### Linting

We use **ruff** for linting. All code must pass lint checks before merging.

```bash
# Check for lint errors
ruff check src/

# Auto-fix fixable issues
ruff check src/ --fix

# Check specific file
ruff check src/timetracer/plugins/httpx_plugin.py
```

### Formatting

```bash
# Format code (optional, ruff handles most)
ruff format src/
```

### Pre-Commit Checklist

Before committing, run:

```bash
# 1. Lint check
ruff check src/

# 2. Run tests
pytest tests/ -v
python examples/fastapi_httpx/test_complete.py

# 3. Verify imports
python -c "from timetracer import TraceConfig, TraceMode"
```

## Making Changes

1. Create a branch: `git checkout -b feature/my-feature`
2. Make your changes
3. Run lint: `ruff check src/`
4. Run tests: `pytest tests/ -v`
5. Commit with a descriptive message
6. Push and open a Pull Request

## Code Style

- Follow PEP 8
- Use type hints for all public functions
- Keep functions focused and small
- Add docstrings to public APIs
- No emojis in code output (use plain text: [OK], [WARN], [ERR])

## Testing Guidelines

- Add tests for new features
- Use pytest fixtures for common setup
- Test both record and replay modes
- Test error cases

### Test File Locations

| Test Type | Location |
|-----------|----------|
| Unit tests | `tests/` |
| Integration tests | `examples/fastapi_httpx/test_complete.py` |
| Edge case tests | `examples/full_integration/test_edge_cases.py` |
| E2E tests | `examples/full_integration/test_e2e_real.py` |

## Good First Issues

Looking to contribute? Check out issues labeled:
- `good first issue` - Simple, well-defined tasks
- `help wanted` - We need community help

## Pull Request Guidelines

1. **Title**: Clear, concise description
2. **Description**: Explain what and why
3. **Tests**: Include tests for new functionality
4. **Lint**: All lint checks must pass
5. **Docs**: Update README if adding features

## Questions?

Open an issue or discussion on GitHub.

---

Thank you for contributing!
