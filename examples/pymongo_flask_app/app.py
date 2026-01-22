"""
Simple Flask + PyMongo app demonstrating Timetracer integration.

Run with:
    # Record mode
    TIMETRACER_MODE=record python app.py
    
    # Replay mode
    TIMETRACER_MODE=replay TIMETRACER_CASSETTE=./cassettes/latest.json python app.py
"""

from flask import Flask, jsonify
from pymongo import MongoClient
from time

tracer.integrations.flask import auto_setup
from timetracer.plugins import enable_pymongo

# Create Flask app with Timetracer
app = auto_setup(Flask(__name__))

# Enable PyMongo plugin
enable_pymongo()

# MongoDB connection
client = MongoClient('mongodb://localhost:27017')
db = client.demo_db


@app.route('/')
def home():
    return jsonify({
        "message": "Welcome to Flask + PyMongo + Timetracer!",
        "endpoints": [
            "GET /users - List all users",
            "GET /users/<id> - Get user by ID",
            "POST /users - Create a user",
        ]
    })


@app.route('/users')
def list_users():
    """List all users from MongoDB."""
    # PyMongo query - will be captured by Timetracer
    users = list(db.users.find({}))
    
    # Convert ObjectId to string for JSON serialization
    for user in users:
        user['_id'] = str(user['_id'])
    
    return jsonify({"users": users, "count": len(users)})


@app.route('/users/<user_id>')
def get_user(user_id):
    """Get a single user by ID."""
    from bson import ObjectId
    
    # PyMongo find_one - captured
    user = db.users.find_one({"_id": ObjectId(user_id)})
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    user['_id'] = str(user['_id'])
    return jsonify(user)


@app.route('/users', methods=['POST'])
def create_user():
    """Create a new user."""
    from flask import request
    
    data = request.get_json()
    
    # PyMongo insert_one - captured
    result = db.users.insert_one({
        "name": data.get("name"),
        "email": data.get("email"),
        "age": data.get("age")
    })
    
    return jsonify({
        "message": "User created",
        "user_id": str(result.inserted_id)
    }), 201


@app.route('/seed')
def seed_data():
    """Seed some demo data."""
    # Clear existing
    db.users.delete_many({})
    
    # Insert test users
    users = [
        {"name": "Alice", "email": "alice@example.com", "age": 30},
        {"name": "Bob", "email": "bob@example.com", "age": 25},
        {"name": "Charlie", "email": "charlie@example.com", "age": 35},
    ]
    
    result = db.users.insert_many(users)
    
    return jsonify({
        "message": "Database seeded",
        "inserted": len(result.inserted_ids)
    })


if __name__ == '__main__':
    print("\n" + "="*60)
    print("Flask + PyMongo + Timetracer Demo")
    print("="*60)
    print("\nEndpoints:")
    print("  GET  /         - Home")
    print("  GET  /seed     - Seed test data")
    print("  GET  /users    - List all users")
    print("  GET  /users/ID - Get user by ID")
    print("  POST /users    - Create user")
    print("\nTips:")
    print("  1. Visit /seed to create test data")
    print("  2. Visit /users to see all users")
    print("  3. Check ./cassettes/ for recorded operations")
    print("="*60 + "\n")
    
    app.run(debug=True, port=5000)
