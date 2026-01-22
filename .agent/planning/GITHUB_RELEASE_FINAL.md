## 🎉 Timetracer v1.5.0: Compression + Motor/MongoDB

Two major features that make debugging production issues even easier!

---

### ✨ Highlights

#### 🗜️ **Cassette Compression**
Reduce cassette file sizes by **60-95%** with gzip compression:

```bash
# Enable compression
export TIMETRACER_COMPRESSION=gzip
TIMETRACER_MODE=record uvicorn app:app
```

**Real-world performance:**
```
Uncompressed:  44,662 bytes
Compressed:     1,915 bytes
Reduction:      95.7% 🎯
```

**Benefits:**
- ✅ Smaller git repositories
- ✅ Faster CI/CD artifact uploads
- ✅ Reduced S3 storage costs
- ✅ Zero-config replay (auto-detects `.json.gz`)

#### 🍃 **Motor/MongoDB Plugin**
Full async MongoDB support for modern Python applications:

```python
from motor.motor_asyncio import AsyncIOMotorClient
from timetracer.plugins import enable_motor

enable_motor()

client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client.mydb

# All operations automatically captured
await db.users.insert_one({"name": "Alice", "age": 30})
user = await db.users.find_one({"name": "Alice"})
```

**Supported operations:**
- `find_one`, `find` (cursor creation)
- `insert_one`, `insert_many`
- `update_one`, `update_many`, `replace_one`
- `delete_one`, `delete_many`
- `count_documents`
- `aggregate` (pipelines)

**Features:**
- ✅ Full async/await support
- ✅ Automatic ObjectId & DateTime serialization
- ✅ Sensitive field redaction
- ✅ Error capture with full context
- ✅ pytest fixture integration

---

### 📦 Installation

```bash
# Full installation
pip install --upgrade timetracer[all]

# MongoDB support only
pip install --upgrade timetracer[motor]

# Compression is included in core package
pip install --upgrade timetracer
```

---

### 📚 Documentation

**New docs:**
- [Compression Guide](https://github.com/usv240/timetracer/blob/main/docs/compression.md)
- [Motor/MongoDB Integration](https://github.com/usv240/timetracer/blob/main/docs/motor.md)
- [Changelog](https://github.com/usv240/timetracer/blob/main/CHANGELOG.md)

**Updated docs:**
- [README](https://github.com/usv240/timetracer/blob/main/README.md)
- [Configuration Reference](https://github.com/usv240/timetracer/blob/main/docs/configuration.md)
- [Roadmap](https://github.com/usv240/timetracer/blob/main/ROADMAP.md)

---

### 🧪 Quality & Testing

- ✅ **149/149 tests passing** (100% success rate)
- ✅ **Compression tests:** 3/3 passing
- ✅ **Motor plugin tests:** 13/13 passing
- ✅ **Full example projects** with working demos
- ✅ **Performance benchmarks** included

**New examples:**
- [`examples/compression_example/`](https://github.com/usv240/timetracer/tree/main/examples/compression_example) - Compression demo with size comparison script
- [`examples/motor_mongodb/`](https://github.com/usv240/timetracer/tree/main/examples/motor_mongodb) - Motor integration example

---

### 🐛 Bug Fixes

- Fixed Windows path escaping in dashboard JavaScript
- Improved error messages for missing cassettes
- Enhanced serialization for MongoDB data types (ObjectId, DateTime)

---

### 🔄 Breaking Changes

**None.** This release is fully backward compatible with v1.4.0.

---

### 📈 Migration Guide

No migration needed! Existing cassettes work as-is.

**To enable compression for new recordings:**

```python
# Option 1: Environment variable
export TIMETRACER_COMPRESSION=gzip

# Option 2: Code configuration
from timetracer import TraceConfig, CompressionType

config = TraceConfig(compression=CompressionType.GZIP)
```

---

### 🚀 What's Next?

Working on **v1.6.0** with:
- PyMongo (sync MongoDB) support
- Litestar framework integration
- Starlette native support

Follow progress on our [Roadmap](https://github.com/usv240/timetracer/blob/main/ROADMAP.md)!

---

### 🙏 Thank You

Thank you to everyone who contributed feedback, bug reports, and feature requests. Your input makes Timetracer better!

---

### 📝 Full Release Notes

See [RELEASE_NOTES.md](https://github.com/usv240/timetracer/blob/main/RELEASE_NOTES.md) for complete details.

---

### 🔗 Links

- 📦 [PyPI Package](https://pypi.org/project/timetracer/)
- 📖 [Documentation](https://github.com/usv240/timetracer#readme)
- 🐛 [Issue Tracker](https://github.com/usv240/timetracer/issues)
- 💬 [Discussions](https://github.com/usv240/timetracer/discussions)

---

**Install now:**
```bash
pip install --upgrade timetracer[all]
```

Happy debugging! 🐛🔍
