"""
Example FastAPI app with Motor/MongoDB integration.

This demonstrates using Timetracer to capture MongoDB operations.

Prerequisites:
    pip install fastapi uvicorn motor

    # MongoDB must be running:
    docker run -d -p 27017:27017 --name mongo mongo

Run:
    TIMETRACER_MODE=record python app.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from timetracer import TraceConfig
from timetracer.integrations.fastapi import TimeTracerMiddleware
from timetracer.plugins import enable_httpx, enable_motor


# =============================================================================
# Models
# =============================================================================

class UserCreate(BaseModel):
    name: str
    email: str
    age: int = 0


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    age: int


# =============================================================================
# MongoDB Setup
# =============================================================================

# MongoDB client (will be initialized on startup)
db = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage MongoDB connection lifecycle."""
    global db
    
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        
        # Connect to MongoDB
        client = AsyncIOMotorClient("mongodb://localhost:27017")
        db = client.timetracer_example
        
        # Verify connection
        await client.admin.command("ping")
        print("Connected to MongoDB")
        
        yield
        
        # Cleanup
        client.close()
        print("Disconnected from MongoDB")
        
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        print("Running in demo mode without MongoDB")
        yield


# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(
    title="Motor/MongoDB Example",
    lifespan=lifespan,
)

# Configure Timetracer
config = TraceConfig.from_env()
app.add_middleware(TimeTracerMiddleware, config=config)

# Enable plugins
enable_motor()
enable_httpx()


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "mongodb": db is not None}


@app.post("/users", response_model=UserResponse)
async def create_user(user: UserCreate):
    """Create a new user."""
    if db is None:
        raise HTTPException(503, "MongoDB not connected")
    
    doc = user.model_dump()
    result = await db.users.insert_one(doc)
    
    return UserResponse(
        id=str(result.inserted_id),
        **doc,
    )


@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """Get a user by ID."""
    if db is None:
        raise HTTPException(503, "MongoDB not connected")
    
    from bson import ObjectId
    
    try:
        doc = await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        raise HTTPException(400, "Invalid user ID")
    
    if not doc:
        raise HTTPException(404, "User not found")
    
    return UserResponse(
        id=str(doc["_id"]),
        name=doc["name"],
        email=doc["email"],
        age=doc.get("age", 0),
    )


@app.get("/users")
async def list_users(limit: int = 10):
    """List all users."""
    if db is None:
        raise HTTPException(503, "MongoDB not connected")
    
    cursor = db.users.find().limit(limit)
    users = []
    
    async for doc in cursor:
        users.append({
            "id": str(doc["_id"]),
            "name": doc["name"],
            "email": doc["email"],
            "age": doc.get("age", 0),
        })
    
    count = await db.users.count_documents({})
    
    return {"users": users, "total": count}


@app.delete("/users/{user_id}")
async def delete_user(user_id: str):
    """Delete a user."""
    if db is None:
        raise HTTPException(503, "MongoDB not connected")
    
    from bson import ObjectId
    
    try:
        result = await db.users.delete_one({"_id": ObjectId(user_id)})
    except Exception:
        raise HTTPException(400, "Invalid user ID")
    
    if result.deleted_count == 0:
        raise HTTPException(404, "User not found")
    
    return {"deleted": True}


# =============================================================================
# Demo
# =============================================================================

def demo():
    """Run a demo without MongoDB (tests plugin loading)."""
    print("=" * 60)
    print("Motor/MongoDB Plugin Demo")
    print("=" * 60)
    print()
    print(f"Timetracer mode: {config.mode.value}")
    print(f"Motor plugin loaded: Yes")
    print()
    
    # Test with TestClient (doesn't need real MongoDB)
    print("Testing endpoints (will fail without MongoDB)...")
    
    client = TestClient(app)
    
    response = client.get("/")
    print(f"  GET / -> {response.status_code}: {response.json()}")
    
    # This will fail without MongoDB, which is expected
    response = client.get("/users")
    print(f"  GET /users -> {response.status_code}")
    
    print()
    print("To run with MongoDB:")
    print("  1. docker run -d -p 27017:27017 mongo")
    print("  2. TIMETRACER_MODE=record uvicorn app:app")
    print()


if __name__ == "__main__":
    demo()
