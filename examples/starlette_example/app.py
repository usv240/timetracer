"""
Starlette Example with Timetracer

Demonstrates time-travel debugging for a Starlette application.

Run:
    # Record mode (capture all external calls)
    TIMETRACER_MODE=record python app.py
    
    # Replay mode (mock external calls)
    TIMETRACER_MODE=replay TIMETRACER_CASSETTE=cassettes/your-cassette.json python app.py
    
    # Or use uvicorn
    TIMETRACER_MODE=record uvicorn app:app --reload
"""

import httpx
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from timetracer.integrations.starlette import auto_setup

# ============================================================================
# API Endpoints
# ============================================================================


async def homepage(request):
    """Simple homepage endpoint."""
    return JSONResponse({
        "message": "Welcome to the Starlette + Timetracer example!",
        "endpoints": [
            "/",
            "/user/{username}",
            "/repos/{username}",
            "/weather/{city}",
        ],
    })


async def get_user(request):
    """
    Fetch user info from GitHub API.
    
    This demonstrates httpx tracking - the external call
    is recorded and can be replayed later.
    """
    username = request.path_params["username"]
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.github.com/users/{username}")
        
        if response.status_code == 404:
            return JSONResponse(
                {"error": f"User '{username}' not found"},
                status_code=404,
            )
        
        data = response.json()
        
        return JSONResponse({
            "username": data["login"],
            "name": data.get("name"),
            "bio": data.get("bio"),
            "public_repos": data.get("public_repos"),
            "followers": data.get("followers"),
        })


async def get_repos(request):
    """
    Fetch user's repositories from GitHub API.
    
    Demonstrates multiple external calls being tracked.
    """
    username = request.path_params["username"]
    
    async with httpx.AsyncClient() as client:
        # Call 1: Get user info
        user_response = await client.get(f"https://api.github.com/users/{username}")
        
        if user_response.status_code == 404:
            return JSONResponse(
                {"error": f"User '{username}' not found"},
                status_code=404,
            )
        
        # Call 2: Get repositories
        repos_response = await client.get(f"https://api.github.com/users/{username}/repos")
        repos = repos_response.json()
        
        # Return top 5 repos by stars
        sorted_repos = sorted(repos, key=lambda r: r.get("stargazers_count", 0), reverse=True)
        top_repos = [
            {
                "name": repo["name"],
                "description": repo.get("description"),
                "stars": repo.get("stargazers_count", 0),
                "url": repo["html_url"],
            }
            for repo in sorted_repos[:5]
        ]
        
        return JSONResponse({
            "username": username,
            "total_repos": len(repos),
            "top_repos": top_repos,
        })


async def get_weather(request):
    """
    Fetch weather data from wttr.in.
    
    Demonstrates tracking of different external APIs.
    """
    city = request.path_params["city"]
    
    async with httpx.AsyncClient() as client:
        # wttr.in provides a JSON API
        response = await client.get(f"https://wttr.in/{city}?format=j1")
        
        if response.status_code != 200:
            return JSONResponse(
                {"error": f"Could not fetch weather for '{city}'"},
                status_code=500,
            )
        
        data = response.json()
        current = data["current_condition"][0]
        
        return JSONResponse({
            "city": city,
            "temperature_c": current["temp_C"],
            "temperature_f": current["temp_F"],
            "description": current["weatherDesc"][0]["value"],
            "humidity": current["humidity"],
            "wind_speed_kmph": current["windspeedKmph"],
        })


# ============================================================================
# Application Setup
# ============================================================================

# Create Starlette app
app = Starlette(
    debug=True,
    routes=[
        Route("/", homepage),
        Route("/user/{username}", get_user),
        Route("/repos/{username}", get_repos),
        Route("/weather/{city}", get_weather),
    ],
)

# Add Timetracer with auto_setup (one-liner!)
# This adds middleware and enables the httpx plugin
auto_setup(app, plugins=["httpx"])


# ============================================================================
# Demo Runner
# ============================================================================

def demo():
    """Run a demo of the application."""
    from starlette.testclient import TestClient
    from timetracer.config import TraceConfig
    from pathlib import Path
    
    config = TraceConfig.from_env()
    
    print("=" * 60)
    print("Starlette + Timetracer Demo")
    print("=" * 60)
    print(f"\nMode: {config.mode.value}")
    print(f"Cassette dir: {config.cassette_dir}")
    print()
    
    client = TestClient(app)
    
    # Test endpoints
    print("Testing endpoints...")
    print()
    
    # 1. Homepage
    print("1. GET / (homepage)")
    response = client.get("/")
    print(f"   Status: {response.status_code}")
    print(f"   Message: {response.json()['message']}")
    print()
    
    # 2. GitHub user
    print("2. GET /user/octocat (GitHub API)")
    response = client.get("/user/octocat")
    if response.status_code == 200:
        data = response.json()
        print(f"   Status: {response.status_code}")
        print(f"   Username: {data['username']}")
        print(f"   Name: {data.get('name', 'N/A')}")
        print(f"   Repos: {data['public_repos']}")
    else:
        print(f"   Status: {response.status_code}")
    print()
    
    # 3. GitHub repos
    print("3. GET /repos/octocat (GitHub API - multiple calls)")
    response = client.get("/repos/octocat")
    if response.status_code == 200:
        data = response.json()
        print(f"   Status: {response.status_code}")
        print(f"   Total repos: {data['total_repos']}")
        print(f"   Top repo: {data['top_repos'][0]['name']}")
    else:
        print(f"   Status: {response.status_code}")
    print()
    
    # Show cassettes if in record mode
    if config.mode.value == "record":
        cassette_dir = Path(config.cassette_dir)
        if cassette_dir.exists():
            cassettes = list(cassette_dir.rglob("*.json"))
            if cassettes:
                print("=" * 60)
                print(f"Recorded {len(cassettes)} cassettes:")
                for cassette in cassettes:
                    size = cassette.stat().st_size
                    print(f"  - {cassette.name} ({size:,} bytes)")
                
                print()
                print("To replay, run:")
                print(f"  TIMETRACER_MODE=replay TIMETRACER_CASSETTE={cassettes[0]} python app.py")
    
    print()
    print("Done!")


if __name__ == "__main__":
    demo()
