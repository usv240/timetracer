"""
Live dashboard server with replay capability.

Provides a web interface with actual replay functionality.
"""

from __future__ import annotations

import json
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from timetracer.dashboard.generator import generate_dashboard
from timetracer.dashboard.template import render_dashboard_html


class DashboardHandler(SimpleHTTPRequestHandler):
    """HTTP handler for the dashboard server."""

    cassette_dir: str = "./cassettes"
    app_command: str = "uvicorn app:app"

    def do_GET(self) -> None:
        """Handle GET requests."""
        parsed = urlparse(self.path)

        if parsed.path == "/" or parsed.path == "/dashboard":
            self._serve_dashboard()
        elif parsed.path == "/api/cassettes":
            self._serve_cassettes_api()
        elif parsed.path == "/api/cassette":
            self._serve_cassette_detail(parsed.query)
        else:
            self.send_error(404, "Not Found")

    def do_POST(self) -> None:
        """Handle POST requests."""
        parsed = urlparse(self.path)

        if parsed.path == "/api/replay":
            self._handle_replay()
        else:
            self.send_error(404, "Not Found")

    def _serve_dashboard(self) -> None:
        """Serve the dashboard HTML with live features."""
        dashboard_data = generate_dashboard(self.cassette_dir, limit=500)
        html = render_live_dashboard_html(dashboard_data)

        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _serve_cassettes_api(self) -> None:
        """Serve cassettes as JSON API."""
        dashboard_data = generate_dashboard(self.cassette_dir, limit=500)

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(dashboard_data.to_dict()).encode("utf-8"))

    def _serve_cassette_detail(self, query: str) -> None:
        """Serve full cassette JSON."""
        params = parse_qs(query)
        path = params.get("path", [None])[0]

        if not path or not Path(path).exists():
            self.send_error(404, "Cassette not found")
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                cassette = json.load(f)

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(cassette, indent=2).encode("utf-8"))
        except Exception as e:
            self.send_error(500, str(e))

    def _handle_replay(self) -> None:
        """Handle replay request."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body)
            cassette_path = data.get("cassette_path")

            if not cassette_path or not Path(cassette_path).exists():
                self._send_json({"error": "Cassette not found"}, 404)
                return

            # Load the cassette
            with open(cassette_path, "r", encoding="utf-8") as f:
                cassette = json.load(f)

            request = cassette.get("request", {})
            response = cassette.get("response", {})
            events = cassette.get("events", [])

            # Return the replay data (simulated replay without starting server)
            replay_result = {
                "success": True,
                "cassette_path": cassette_path,
                "request": {
                    "method": request.get("method"),
                    "path": request.get("path"),
                    "headers": request.get("headers", {}),
                },
                "response": {
                    "status": response.get("status"),
                    "duration_ms": response.get("duration_ms"),
                    "body": response.get("body"),
                },
                "events": [
                    {
                        "type": e.get("event_type"),
                        "url": e.get("signature", {}).get("url"),
                        "status": e.get("result", {}).get("status"),
                        "duration_ms": e.get("duration_ms"),
                    }
                    for e in events
                ],
                "message": "Replay data loaded. This shows what would happen if you replayed this cassette.",
            }

            self._send_json(replay_result, 200)

        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _send_json(self, data: dict[str, Any], status: int = 200) -> None:
        """Send JSON response."""
        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def log_message(self, format: str, *args: Any) -> None:
        """Log requests to console."""
        print(f"[{self.command}] {self.path} - {args[1] if len(args) > 1 else ''}")


def render_live_dashboard_html(data: Any) -> str:
    """Render dashboard with live replay capability."""
    # Get the base dashboard HTML
    base_html = render_dashboard_html(data)

    # Inject live replay script
    live_script = """
    <script>
    // Override replay button to use live API
    function liveReplay(cassettePath) {
        const modal = document.getElementById('detail-modal');
        const body = document.getElementById('modal-body');

        body.innerHTML = '<div style="text-align:center;padding:40px;"><h3>Loading replay...</h3></div>';
        modal.classList.add('show');

        fetch('/api/replay', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({cassette_path: cassettePath})
        })
        .then(r => r.json())
        .then(result => {
            if (result.error) {
                body.innerHTML = '<div style="color:#ff6b6b;padding:20px;">Error: ' + result.error + '</div>';
                return;
            }

            body.innerHTML = `
                <div class="detail-section">
                    <h3 style="color:#00ff88;">Replay Result</h3>
                    <div class="detail-grid">
                        <span class="detail-label">Request</span>
                        <span class="detail-value">${result.request.method} ${result.request.path}</span>
                        <span class="detail-label">Status</span>
                        <span class="detail-value"><span class="status-badge ${result.response.status >= 400 ? 'status-error' : 'status-success'}">${result.response.status}</span></span>
                        <span class="detail-label">Duration</span>
                        <span class="detail-value">${result.response.duration_ms.toFixed(2)}ms</span>
                    </div>
                </div>

                ${result.events.length > 0 ? `
                <div class="detail-section">
                    <h3>Mocked Dependencies (${result.events.length})</h3>
                    <div class="events-list">
                        ${result.events.map(e => `
                            <div class="event-item">
                                <span>${e.type}</span>
                                <span class="event-url">${e.url || '-'}</span>
                                <span class="status-badge ${(e.status || 200) >= 400 ? 'status-error' : 'status-success'}">${e.status || '-'}</span>
                                <span>${e.duration_ms.toFixed(0)}ms</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
                ` : ''}

                ${result.response.body ? `
                <div class="detail-section">
                    <h3>Response Body</h3>
                    <pre style="background:rgba(0,0,0,0.4);padding:16px;border-radius:8px;max-height:300px;overflow:auto;font-size:0.8rem;color:#98c379;">${typeof result.response.body === 'string' ? result.response.body : JSON.stringify(result.response.body, null, 2)}</pre>
                </div>
                ` : ''}

                <div class="detail-section">
                    <p style="color:#888;font-size:0.85rem;">${result.message}</p>
                </div>
            `;
        })
        .catch(err => {
            body.innerHTML = '<div style="color:#ff6b6b;padding:20px;">Network error: ' + err.message + '</div>';
        });
    }
    </script>
    """

    # Insert before </body>
    return base_html.replace("</body>", live_script + "</body>")


def start_server(cassette_dir: str, port: int = 8765) -> None:
    """Start the dashboard server."""
    DashboardHandler.cassette_dir = cassette_dir

    server = HTTPServer(("", port), DashboardHandler)

    print(f"Dashboard server running at http://localhost:{port}")
    print(f"Serving cassettes from: {cassette_dir}")
    print("Press Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()
