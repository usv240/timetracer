"""
HTML template for dashboard visualization.

Generates a self-contained HTML file with embedded CSS and JavaScript.
Features: sortable table, filters, expandable rows, search.
"""

from __future__ import annotations

import html
import json

from timetracer.dashboard.generator import DashboardData


def render_dashboard_html(data: DashboardData) -> str:
    """
    Render dashboard data as a standalone HTML file.

    Args:
        data: Dashboard data to visualize.

    Returns:
        Complete HTML string.
    """
    # Convert data to JSON for JavaScript
    data_json = json.dumps(data.to_dict(), indent=2)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Timetracer Dashboard</title>
    <style>
{_get_css()}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>Timetracer Dashboard</h1>
            <p class="subtitle">Generated: {html.escape(data.generated_at[:19].replace('T', ' '))}</p>
        </header>

        <div class="stats-row">
            <div class="stat-card">
                <div class="stat-value">{data.total_count}</div>
                <div class="stat-label">Total Requests</div>
            </div>
            <div class="stat-card stat-success">
                <div class="stat-value">{data.success_count}</div>
                <div class="stat-label">Success</div>
            </div>
            <div class="stat-card stat-error">
                <div class="stat-value">{data.error_count}</div>
                <div class="stat-label">Errors</div>
            </div>
        </div>

        <div class="filters-row">
            <input type="text" id="search" placeholder="Search endpoints..." class="search-input">
            <select id="method-filter" class="filter-select">
                <option value="">All Methods</option>
            </select>
            <select id="status-filter" class="filter-select">
                <option value="">All Statuses</option>
                <option value="error">Errors Only</option>
                <option value="success">Success Only</option>
            </select>
            <select id="duration-filter" class="filter-select">
                <option value="">All Durations</option>
                <option value="slow">Slow (>1s)</option>
                <option value="medium">Medium (300ms-1s)</option>
                <option value="fast">Fast (<300ms)</option>
            </select>
            <select id="time-filter" class="filter-select">
                <option value="">All Time</option>
                <option value="1">Last 1 min</option>
                <option value="5">Last 5 mins</option>
                <option value="10">Last 10 mins</option>
                <option value="15">Last 15 mins</option>
                <option value="30">Last 30 mins</option>
                <option value="60">Last 1 hour</option>
                <option value="custom">Custom Range</option>
            </select>
            <div id="custom-time-range" style="display:none;gap:8px;align-items:center;">
                <input type="datetime-local" id="time-from" class="filter-select" style="width:auto;">
                <span style="color:#888;">to</span>
                <input type="datetime-local" id="time-to" class="filter-select" style="width:auto;">
            </div>
            <button id="clear-filters" class="btn btn-secondary">Clear Filters</button>
        </div>

        <div class="table-container">
            <table class="cassette-table">
                <thead>
                    <tr>
                        <th class="sortable" data-sort="recorded_at">Time</th>
                        <th class="sortable" data-sort="method">Method</th>
                        <th class="sortable" data-sort="endpoint">Endpoint</th>
                        <th class="sortable" data-sort="status">Status</th>
                        <th class="sortable" data-sort="duration_ms">Duration</th>
                        <th class="sortable" data-sort="event_count">Events</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="cassette-tbody">
                    <!-- Populated by JavaScript -->
                </tbody>
            </table>
        </div>

        <div id="showing-count" class="showing-count"></div>
    </div>

    <!-- Detail Modal -->
    <div id="detail-modal" class="modal">
        <div class="modal-content">
            <span class="modal-close">&times;</span>
            <div id="modal-body"></div>
        </div>
    </div>

    <script>
        const dashboardData = {data_json};
        {_get_js()}
    </script>
</body>
</html>"""


def _get_css() -> str:
    """Get embedded CSS styles."""
    return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #e0e0e0;
            line-height: 1.6;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 24px;
        }

        .header {
            text-align: center;
            margin-bottom: 32px;
        }

        .header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 8px;
        }

        .subtitle {
            color: #888;
            font-size: 0.9rem;
        }

        .stats-row {
            display: flex;
            gap: 16px;
            margin-bottom: 24px;
            justify-content: center;
        }

        .stat-card {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 20px 40px;
            text-align: center;
            backdrop-filter: blur(10px);
        }

        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            color: #fff;
        }

        .stat-label {
            font-size: 0.85rem;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .stat-success .stat-value { color: #00ff88; }
        .stat-error .stat-value { color: #ff6b6b; }

        .filters-row {
            display: flex;
            gap: 12px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }

        .search-input, .filter-select {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 8px;
            padding: 10px 16px;
            color: #fff;
            font-size: 0.9rem;
            outline: none;
            transition: border-color 0.2s;
        }

        .search-input {
            flex: 1;
            min-width: 200px;
        }

        .search-input:focus, .filter-select:focus {
            border-color: #00d9ff;
        }

        .filter-select option {
            background: #1a1a2e;
        }

        .btn {
            padding: 10px 20px;
            border-radius: 8px;
            border: none;
            cursor: pointer;
            font-size: 0.9rem;
            transition: all 0.2s;
        }

        .btn-secondary {
            background: rgba(255, 255, 255, 0.1);
            color: #fff;
        }

        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.2);
        }

        .btn-primary {
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            color: #1a1a2e;
            font-weight: 600;
        }

        .table-container {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            overflow: hidden;
        }

        .cassette-table {
            width: 100%;
            border-collapse: collapse;
        }

        .cassette-table th {
            background: rgba(0, 0, 0, 0.3);
            padding: 14px 16px;
            text-align: left;
            font-weight: 600;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #aaa;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        .cassette-table th.sortable {
            cursor: pointer;
            user-select: none;
        }

        .cassette-table th.sortable:hover {
            color: #00d9ff;
        }

        .cassette-table th.sortable::after {
            content: ' ↕';
            opacity: 0.3;
        }

        .cassette-table th.sort-asc::after { content: ' ↑'; opacity: 1; }
        .cassette-table th.sort-desc::after { content: ' ↓'; opacity: 1; }

        .cassette-table td {
            padding: 12px 16px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            font-size: 0.9rem;
        }

        .cassette-table tr:hover {
            background: rgba(255, 255, 255, 0.03);
        }

        .cassette-table tr.error-row {
            background: rgba(255, 80, 80, 0.08);
            border-left: 3px solid #ff6b6b;
        }

        .cassette-table tr.error-row:hover {
            background: rgba(255, 80, 80, 0.15);
        }

        .slow-warning {
            color: #ff6b6b;
            font-weight: 600;
        }

        .slow-warning::after {
            content: ' ⚠';
        }

        .method-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }

        .method-GET { background: rgba(0, 200, 150, 0.2); color: #00c896; }
        .method-POST { background: rgba(0, 150, 255, 0.2); color: #0096ff; }
        .method-PUT { background: rgba(255, 180, 0, 0.2); color: #ffb400; }
        .method-DELETE { background: rgba(255, 100, 100, 0.2); color: #ff6464; }
        .method-PATCH { background: rgba(180, 100, 255, 0.2); color: #b464ff; }

        .status-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 600;
        }

        .status-success { background: rgba(0, 255, 136, 0.15); color: #00ff88; }
        .status-error { background: rgba(255, 107, 107, 0.15); color: #ff6b6b; }
        .status-redirect { background: rgba(255, 200, 0, 0.15); color: #ffc800; }

        .endpoint-cell {
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.85rem;
            max-width: 300px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .duration-cell {
            color: #888;
        }

        .duration-slow { color: #ff6b6b; }
        .duration-medium { color: #ffc800; }
        .duration-fast { color: #00ff88; }

        .action-btn {
            padding: 6px 12px;
            border-radius: 6px;
            border: none;
            background: rgba(0, 217, 255, 0.15);
            color: #00d9ff;
            cursor: pointer;
            font-size: 0.8rem;
            transition: all 0.2s;
        }

        .action-btn:hover {
            background: rgba(0, 217, 255, 0.3);
        }

        .showing-count {
            text-align: center;
            padding: 16px;
            color: #666;
            font-size: 0.85rem;
        }

        /* Modal */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            z-index: 1000;
            overflow-y: auto;
        }

        .modal.show {
            display: flex;
            align-items: flex-start;
            justify-content: center;
            padding: 40px 20px;
        }

        .modal-content {
            background: #1a1a2e;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            max-width: 900px;
            width: 100%;
            padding: 24px;
            position: relative;
        }

        .modal-close {
            position: absolute;
            top: 16px;
            right: 20px;
            font-size: 1.5rem;
            cursor: pointer;
            color: #888;
            transition: color 0.2s;
        }

        .modal-close:hover {
            color: #fff;
        }

        .detail-section {
            margin-bottom: 24px;
        }

        .detail-section h3 {
            font-size: 1rem;
            color: #00d9ff;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        .detail-grid {
            display: grid;
            grid-template-columns: 120px 1fr;
            gap: 8px;
            font-size: 0.9rem;
        }

        .detail-label {
            color: #888;
        }

        .detail-value {
            color: #fff;
            font-family: 'Monaco', 'Menlo', monospace;
            word-break: break-all;
        }

        .events-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .event-item {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            padding: 12px;
            display: grid;
            grid-template-columns: 80px 1fr 80px 80px;
            gap: 12px;
            align-items: center;
            font-size: 0.85rem;
        }

        .event-url {
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.8rem;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .copy-btn {
            padding: 8px 16px;
            background: rgba(0, 217, 255, 0.1);
            border: 1px solid rgba(0, 217, 255, 0.3);
            border-radius: 6px;
            color: #00d9ff;
            cursor: pointer;
            font-size: 0.85rem;
            margin-top: 12px;
        }

        .copy-btn:hover {
            background: rgba(0, 217, 255, 0.2);
        }

        /* JSON syntax highlighting */
        .json-key { color: #00d9ff; }
        .json-string { color: #98c379; }
        .json-number { color: #d19a66; }
        .json-boolean { color: #c678dd; }
        .json-null { color: #888; }
    """


def _get_js() -> str:
    """Get embedded JavaScript."""
    return """
        let cassettes = dashboardData.cassettes;
        let sortColumn = 'recorded_at';
        let sortDirection = 'desc';

        function init() {
            populateFilters();
            renderTable();
            setupEventListeners();
        }

        function populateFilters() {
            const methodSelect = document.getElementById('method-filter');
            dashboardData.filters.methods.forEach(method => {
                const opt = document.createElement('option');
                opt.value = method;
                opt.textContent = method;
                methodSelect.appendChild(opt);
            });
        }

        let displayedCassettes = [];

        function renderTable() {
            const tbody = document.getElementById('cassette-tbody');
            const filtered = getFilteredCassettes();
            displayedCassettes = sortCassettes(filtered);

            tbody.innerHTML = displayedCassettes.map((c, idx) => `
                <tr class="${c.status >= 400 ? 'error-row' : ''}">
                    <td>${formatTime(c.recorded_at)}</td>
                    <td><span class="method-badge method-${c.method}">${c.method}</span></td>
                    <td class="endpoint-cell" title="${escapeHtml(c.endpoint)}">${escapeHtml(c.endpoint)}</td>
                    <td><span class="status-badge ${getStatusClass(c.status)}">${c.status}</span></td>
                    <td class="${getDurationClass(c.duration_ms)} ${c.duration_ms > 1000 ? 'slow-warning' : ''}">${c.duration_ms.toFixed(0)}ms</td>
                    <td>${c.event_count}</td>
                    <td>
                        <button class="action-btn view-btn" data-idx="${idx}">View</button>
                        <button class="action-btn replay-btn" data-idx="${idx}" style="background:rgba(0,255,136,0.15);color:#00ff88;margin-left:4px;">Replay</button>
                    </td>
                </tr>
            `).join('');

            // Add click handlers for view buttons
            document.querySelectorAll('.view-btn').forEach(btn => {
                btn.onclick = function() {
                    const idx = parseInt(this.dataset.idx);
                    if (displayedCassettes[idx]) {
                        showDetail(displayedCassettes[idx]);
                    }
                };
            });

            // Add click handlers for replay buttons
            document.querySelectorAll('.replay-btn').forEach(btn => {
                btn.onclick = function() {
                    const idx = parseInt(this.dataset.idx);
                    if (displayedCassettes[idx]) {
                        const c = displayedCassettes[idx];

                        // Check if we're in live server mode (try API first)
                        if (typeof liveReplay === 'function') {
                            liveReplay(c.path);
                        } else {
                            // Static mode: copy command
                            const cmd = 'TIMETRACER_MODE=replay TIMETRACER_CASSETTE="' + c.path + '" uvicorn app:app';
                            navigator.clipboard.writeText(cmd).then(() => {
                                this.textContent = 'Copied!';
                                this.style.background = 'rgba(0,255,136,0.4)';
                                setTimeout(() => {
                                    this.textContent = 'Replay';
                                    this.style.background = 'rgba(0,255,136,0.15)';
                                }, 1500);
                            }).catch(() => {
                                prompt('Copy this command:', cmd);
                            });
                        }
                    }
                };
            });

            document.getElementById('showing-count').textContent =
                `Showing ${displayedCassettes.length} of ${cassettes.length} cassettes`;

            updateSortIndicators();
        }

        function getFilteredCassettes() {
            const search = document.getElementById('search').value.toLowerCase();
            const method = document.getElementById('method-filter').value;
            const status = document.getElementById('status-filter').value;
            const duration = document.getElementById('duration-filter').value;
            const timeFilter = document.getElementById('time-filter').value;
            const timeFrom = document.getElementById('time-from').value;
            const timeTo = document.getElementById('time-to').value;

            const now = new Date();

            return cassettes.filter(c => {
                if (search && !c.endpoint.toLowerCase().includes(search)) return false;
                if (method && c.method !== method) return false;
                if (status === 'error' && c.status < 400) return false;
                if (status === 'success' && c.status >= 400) return false;
                if (duration === 'slow' && c.duration_ms <= 1000) return false;
                if (duration === 'medium' && (c.duration_ms < 300 || c.duration_ms > 1000)) return false;
                if (duration === 'fast' && c.duration_ms >= 300) return false;

                // Time filter
                if (timeFilter && timeFilter !== 'custom') {
                    const recordedAt = new Date(c.recorded_at);
                    const diffMs = now - recordedAt;
                    const diffMins = diffMs / (1000 * 60);
                    if (diffMins > parseInt(timeFilter)) return false;
                }

                // Custom time range
                if (timeFilter === 'custom') {
                    const recordedAt = new Date(c.recorded_at);
                    if (timeFrom && recordedAt < new Date(timeFrom)) return false;
                    if (timeTo && recordedAt > new Date(timeTo)) return false;
                }

                return true;
            });
        }

        function sortCassettes(arr) {
            return [...arr].sort((a, b) => {
                let aVal = a[sortColumn];
                let bVal = b[sortColumn];

                if (typeof aVal === 'string') {
                    aVal = aVal.toLowerCase();
                    bVal = bVal.toLowerCase();
                }

                if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
                if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
                return 0;
            });
        }

        function updateSortIndicators() {
            document.querySelectorAll('.sortable').forEach(th => {
                th.classList.remove('sort-asc', 'sort-desc');
                if (th.dataset.sort === sortColumn) {
                    th.classList.add(sortDirection === 'asc' ? 'sort-asc' : 'sort-desc');
                }
            });
        }

        function setupEventListeners() {
            document.getElementById('search').addEventListener('input', renderTable);
            document.getElementById('method-filter').addEventListener('change', renderTable);
            document.getElementById('status-filter').addEventListener('change', renderTable);
            document.getElementById('duration-filter').addEventListener('change', renderTable);
            document.getElementById('time-filter').addEventListener('change', function() {
                const customDiv = document.getElementById('custom-time-range');
                if (this.value === 'custom') {
                    customDiv.style.display = 'flex';
                } else {
                    customDiv.style.display = 'none';
                }
                renderTable();
            });
            document.getElementById('time-from').addEventListener('change', renderTable);
            document.getElementById('time-to').addEventListener('change', renderTable);
            document.getElementById('clear-filters').addEventListener('click', () => {
                document.getElementById('search').value = '';
                document.getElementById('method-filter').value = '';
                document.getElementById('status-filter').value = '';
                document.getElementById('duration-filter').value = '';
                document.getElementById('time-filter').value = '';
                document.getElementById('time-from').value = '';
                document.getElementById('time-to').value = '';
                document.getElementById('custom-time-range').style.display = 'none';
                renderTable();
            });

            document.querySelectorAll('.sortable').forEach(th => {
                th.addEventListener('click', () => {
                    if (sortColumn === th.dataset.sort) {
                        sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
                    } else {
                        sortColumn = th.dataset.sort;
                        sortDirection = 'desc';
                    }
                    renderTable();
                });
            });

            document.querySelector('.modal-close').addEventListener('click', hideModal);
            document.getElementById('detail-modal').addEventListener('click', e => {
                if (e.target.id === 'detail-modal') hideModal();
            });
        }

        let currentCassette = null;

        function showDetail(c) {
            if (!c) return;
            currentCassette = c;

            const modal = document.getElementById('detail-modal');
            const body = document.getElementById('modal-body');

            body.innerHTML = `
                <div class="detail-section">
                    <h3>Request Overview</h3>
                    <div class="detail-grid">
                        <span class="detail-label">Method</span>
                        <span class="detail-value"><span class="method-badge method-${c.method}">${c.method}</span></span>
                        <span class="detail-label">Endpoint</span>
                        <span class="detail-value">${escapeHtml(c.endpoint)}</span>
                        <span class="detail-label">Status</span>
                        <span class="detail-value"><span class="status-badge ${getStatusClass(c.status)}">${c.status}</span></span>
                        <span class="detail-label">Duration</span>
                        <span class="detail-value">${c.duration_ms.toFixed(2)}ms</span>
                        <span class="detail-label">Recorded</span>
                        <span class="detail-value">${c.recorded_at}</span>
                        <span class="detail-label">File</span>
                        <span class="detail-value">${escapeHtml(c.filename)}</span>
                    </div>
                </div>

                ${c.events.length > 0 ? `
                <div class="detail-section">
                    <h3>Dependency Events (${c.events.length})</h3>
                    <div class="events-list">
                        ${c.events.map(e => `
                            <div class="event-item">
                                <span class="method-badge method-${e.method || 'GET'}">${e.method || e.type}</span>
                                <span class="event-url" title="${escapeHtml(e.url || '')}">${escapeHtml(e.url || e.type)}</span>
                                <span class="status-badge ${getStatusClass(e.status || 200)}">${e.status || '-'}</span>
                                <span class="${getDurationClass(e.duration_ms)}">${e.duration_ms.toFixed(0)}ms</span>
                            </div>
                        `).join('')}
                    </div>
                ` : ''}

                ${c.error_info ? `
                <div class="detail-section">
                    <h3 style="color:#ff6b6b;">⚠ Error Details</h3>
                    <div class="detail-grid">
                        <span class="detail-label">Type</span>
                        <span class="detail-value" style="color:#ff6b6b;">${escapeHtml(c.error_info.type || 'Unknown')}</span>
                        <span class="detail-label">Message</span>
                        <span class="detail-value">${escapeHtml(c.error_info.message || 'No message')}</span>
                    </div>
                    ${c.error_info.traceback ? `
                    <h4 style="margin-top:16px;color:#888;">Stack Trace</h4>
                    <pre style="background:rgba(255,80,80,0.1);border:1px solid rgba(255,80,80,0.3);padding:16px;border-radius:8px;font-size:0.75rem;max-height:300px;overflow:auto;color:#ccc;white-space:pre-wrap;">${escapeHtml(c.error_info.traceback)}</pre>
                    ` : ''}
                </div>
                ` : ''}

                <div class="detail-section">
                    <h3>Replay Command</h3>
                    <code id="replay-cmd" class="detail-value" style="display:block;background:rgba(0,0,0,0.3);padding:12px;border-radius:8px;font-size:0.8rem;"></code>
                    <button class="copy-btn" id="copy-btn">Copy Command</button>
                </div>

                <div class="detail-section">
                    <h3 style="cursor:pointer" onclick="toggleRawJson()">
                        Raw JSON <span id="json-toggle">▼</span>
                    </h3>
                    <pre id="raw-json" style="display:none;background:rgba(0,0,0,0.4);padding:16px;border-radius:8px;font-size:0.75rem;max-height:400px;overflow:auto;color:#aaa;"></pre>
                </div>
            `;

            // Set replay command text (avoids escaping issues)
            document.getElementById('replay-cmd').textContent =
                'TIMETRACER_MODE=replay TIMETRACER_CASSETTE="' + c.path + '" uvicorn app:app';

            // Set raw JSON with syntax highlighting
            document.getElementById('raw-json').innerHTML = syntaxHighlight(JSON.stringify(c, null, 2));

            // Add copy button handler
            document.getElementById('copy-btn').onclick = copyReplayCommand;

            modal.classList.add('show');
        }

        function toggleRawJson() {
            const el = document.getElementById('raw-json');
            const toggle = document.getElementById('json-toggle');
            if (el.style.display === 'none') {
                el.style.display = 'block';
                toggle.textContent = '▲';
            } else {
                el.style.display = 'none';
                toggle.textContent = '▼';
            }
        }

        function hideModal() {
            document.getElementById('detail-modal').classList.remove('show');
        }

        function copyReplayCommand() {
            if (!currentCassette) return;
            const cmd = 'TIMETRACER_MODE=replay TIMETRACER_CASSETTE="' + currentCassette.path + '" uvicorn app:app';
            navigator.clipboard.writeText(cmd).then(() => {
                alert('Copied to clipboard!');
            }).catch(() => {
                prompt('Copy this command:', cmd);
            });
        }

        function formatTime(isoString) {
            if (!isoString) return '-';
            return isoString.substring(11, 19);
        }

        function getStatusClass(status) {
            if (status >= 400) return 'status-error';
            if (status >= 300) return 'status-redirect';
            return 'status-success';
        }

        function getDurationClass(ms) {
            if (ms > 1000) return 'duration-cell duration-slow';
            if (ms > 300) return 'duration-cell duration-medium';
            return 'duration-cell duration-fast';
        }

        function escapeHtml(str) {
            if (!str) return '';
            return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }

        function syntaxHighlight(json) {
            json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\\s*:)?|\b(true|false|null)\b|-?\\d+(?:\\.\\d*)?(?:[eE][+\\-]?\\d+)?)/g, function (match) {
                let cls = 'json-number';
                if (/^"/.test(match)) {
                    if (/:$/.test(match)) {
                        cls = 'json-key';
                    } else {
                        cls = 'json-string';
                    }
                } else if (/true|false/.test(match)) {
                    cls = 'json-boolean';
                } else if (/null/.test(match)) {
                    cls = 'json-null';
                }
                return '<span class="' + cls + '">' + match + '</span>';
            });
        }

        init();
    """
