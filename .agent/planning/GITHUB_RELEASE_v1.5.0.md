# Release v1.5.0 - Compression + Motor/MongoDB Support

**Release Date:** 2026-01-22

---

## 🎉 Highlights

Two major features that significantly enhance Timetracer's capabilities:

### ✨ **Cassette Compression** 
Gzip compression with **60-95% file size reduction**

### 🚀 **Motor/MongoDB Plugin**
Full async MongoDB support for modern Python applications

---

## 📦 Installation

```bash
# Full installation
pip install timetracer[all]

# Specific features
pip install timetracer[motor]  # MongoDB support
pip install timetracer          # Compression included in core
```

---

## 🔥 New Features

### Cassette Compression

Reduce cassette file sizes by 60-95% with gzip compression:

```bash
# Enable via environment variable
export TIMETRACER_COMPRESSION=gzip
TIMETRACER_MODE=record uvicorn app:app

# Or via code
from timetracer import TraceConfig, CompressionType

config = TraceConfig(
    mode="record",
    compression=CompressionType.GZIP,
)
```

**Key Benefits:**
- ✅ **60-95% smaller files** (tested with real-world cassettes)
- ✅ **Transparent replay** - Auto-detection of `.json.gz` files
- ✅ **Faster CI/CD** - Smaller artifacts to upload/download
- ✅ **Safe for git** - Commit compressed cassettes to repos

**Example Performance:**
```
Uncompressed: 44,662 bytes
Compressed:    1,915 bytes
Reduction:     95.7%
```

### Motor/MongoDB Plugin

Record and replay async MongoDB operations:

```python
from motor.motor_asyncio import AsyncIOMotorClient
from timetracer.plugins import enable_motor

enable_motor()

client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client.mydb

# All operations are automatically captured
await db.users.insert_one({"name": "Alice", "age": 30})
user = await db.users.find_one({"name": "Alice"})
```

**Supported Operations:**
- `find_one`, `find` (cursor)
- `insert_one`, `insert_many`
- `update_one`, `update_many`
- `delete_one`, `delete_many`
- `count_documents`
- `aggregate` (pipelines)

**Features:**
- ✅ Full async/await support
- ✅ Automatic ObjectId serialization
- ✅ DateTime handling
- ✅ Sensitive field redaction
- ✅ Error capture and replay
- ✅ Integration with pytest fixtures

---

## 📚 Documentation

**New Documentation:**
- [Compression Guide](docs/compression.md)
- [Motor/MongoDB Integration](docs/motor.md)
- [Changelog](CHANGELOG.md)

**Updated Documentation:**
- [README](README.md) - Added compression and Motor features
- [Configuration Reference](docs/configuration.md) - Added `TIMETRACER_COMPRESSION` variable
- [Roadmap](ROADMAP.md) - Marked v1.5.0 as completed

---

## 🧪 Quality & Testing

**Test Coverage:**
- ✅ **149/149 tests passing** (100% success rate)
- ✅ Compression tests: 3/3 passing
- ✅ Motor plugin tests: 13/13 passing
- ✅ Integration examples for all features
- ✅ Performance benchmarks included

**New Examples:**
- `examples/compression_example/` - Compression demo with size comparison
- `examples/motor_mongodb/` - Motor integration example

---

## 🐛 Bug Fixes

- Fixed Windows path escaping in dashboard JavaScript
- Improved error messages for missing cassettes
- Enhanced serialization for MongoDB data types (ObjectId, DateTime)

---

## 🔄 Breaking Changes

**None.** This release is fully backward compatible.

---

## 📈 Migration Guide

No migration needed! Existing cassettes continue to work.

**To enable compression for new recordings:**

```bash
# Option 1: Environment variable
export TIMETRACER_COMPRESSION=gzip

# Option 2: Code configuration
from timetracer import CompressionType

config = TraceConfig(compression=CompressionType.GZIP)
```

---

## 🙏 Contributors

Thank you to everyone who contributed to this release!

---

## 📝 Full Changelog

See [CHANGELOG.md](CHANGELOG.md) for complete version history.

---

## 🔗 Links

- [PyPI Package](https://pypi.org/project/timetracer/)
- [GitHub Repository](https://github.com/usv240/timetracer)
- [Documentation](https://github.com/usv240/timetracer#readme)
- [Issue Tracker](https://github.com/usv240/timetracer/issues)

---

## 🚀 What's Next?

Stay tuned for **v1.6.0** coming soon with:
- PyMongo (sync MongoDB) support
- Litestar framework integration
- Starlette native support

Follow development on [GitHub](https://github.com/usv240/timetracer)!
