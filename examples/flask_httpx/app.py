"""
Flask + httpx Example for Timetrace

Demonstrates:
- Flask middleware integration
- httpx outbound call recording
- Replay with mocked dependencies
"""

from flask import Flask, jsonify
import httpx

from timetrace.integrations.flask import init_app
from timetrace.config import TraceConfig
from timetrace.plugins import enable_httpx

# Create Flask app
app = Flask(__name__)

# Configure Timetrace
config = TraceConfig.from_env()
init_app(app, config)

# Enable httpx plugin
enable_httpx()


@app.route("/")
def health():
    """Health check endpoint (excluded from tracing)."""
    return jsonify({"status": "ok"})


@app.route("/weather/<city>")
def get_weather(city: str):
    """
    Get weather for a city.
    
    Makes an outbound HTTP call that will be recorded/replayed.
    """
    # This call will be captured in record mode
    # and mocked in replay mode
    with httpx.Client() as client:
        response = client.get(
            f"https://httpbin.org/get",
            params={"city": city}
        )
    
    return jsonify({
        "city": city,
        "external_response": response.json(),
    })


@app.route("/checkout", methods=["POST"])
def checkout():
    """
    Checkout endpoint.
    
    Simulates calling a payment API.
    """
    with httpx.Client() as client:
        # Simulate payment call
        response = client.post(
            "https://httpbin.org/post",
            json={"amount": 99.99, "currency": "USD"}
        )
    
    return jsonify({
        "status": "success",
        "payment_id": "pay_123",
        "external_status": response.status_code,
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
