#!/usr/bin/env python3
import json
import sqlite3
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

DB_PATH = os.environ.get("FLAKE_DB", "flake.db")
PORT = int(os.environ.get("FLAKE_PORT", "8080"))
STATIC_DIR = Path(__file__).parent / "web" / "static"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path in ("/", "/index.html"):
            self._serve_file("index.html", "text/html")
            return
        if path.startswith("/static/"):
            fname = path[len("/static/"):]
            content_types = {".html": "text/html", ".css": "text/css", ".js": "application/javascript"}
            ext = Path(fname).suffix
            ct = content_types.get(ext, "application/octet-stream")
            self._serve_file(fname, ct)
            return
        handlers = {
            "/api/stats": self.api_stats,
            "/api/flake-rate": self.api_flake_rate,
            "/api/breakdown": self.api_breakdown,
            "/api/heatmap": self.api_heatmap,
            "/api/top-flakes": self.api_top_flakes,
            "/api/devices": self.api_devices,
            "/api/by-action": self.api_by_action,
            "/api/by-platform": self.api_by_platform,
            "/api/volume": self.api_volume,
            "/api/duration-dist": self.api_duration_dist,
            "/api/classification-trend": self.api_classification_trend,
            "/api/sessions": self.api_sessions,
            "/api/latest-session": self.api_latest_session,
        }
        h = handlers.get(path)
        if h:
            h()
        else:
            self.send_response(404)
            self.end_headers()

    def _serve_file(self, filename, content_type):
        filepath = STATIC_DIR / filename
        if not filepath.exists():
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(filepath.read_bytes())

    def _json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _query(self, sql, params=()):
        db = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
        try:
            return [dict(r) for r in db.execute(sql, params).fetchall()]
        finally:
            db.close()

    def _scalar(self, sql, params=()):
        rows = self._query(sql, params)
        if rows:
            return list(rows[0].values())[0]
        return 0

    def api_stats(self):
        rows = self._query("""
            SELECT
                COUNT(*) as total_runs,
                SUM(CASE WHEN result != 'passed' THEN 1 ELSE 0 END) as fail_count,
                SUM(CASE WHEN classification IS NOT NULL THEN 1 ELSE 0 END) as classified_count,
                SUM(CASE WHEN classification = 'REAL_BUG' THEN 1 ELSE 0 END) as real_bug_count
            FROM test_runs
        """)
        s = rows[0]
        s["flake_rate"] = round(s["fail_count"] / s["total_runs"] * 100, 1) if s["total_runs"] else 0
        avg_dur = self._scalar("SELECT CAST(ROUND(AVG(duration_ms / 1000.0)) AS INTEGER) FROM test_runs")
        s["avg_duration"] = avg_dur or 0
        dr = self._query("SELECT MIN(DATE(run_at)) as first, MAX(DATE(run_at)) as last FROM test_runs")
        if dr and dr[0]["first"] and dr[0]["last"]:
            s["date_range"] = f"{dr[0]['first']} to {dr[0]['last']}"
        else:
            s["date_range"] = ""
        self._json(s)

    def api_flake_rate(self):
        rows = self._query("""
            SELECT DATE(run_at) as day,
                   ROUND(SUM(CASE WHEN result != 'passed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as rate
            FROM test_runs
            GROUP BY day ORDER BY day LIMIT 60
        """)
        self._json(rows)

    def api_breakdown(self):
        rows = self._query("""
            SELECT COALESCE(classification, 'UNCLASSIFIED') as classification, COUNT(*) as count
            FROM test_runs WHERE result != 'passed'
            GROUP BY classification ORDER BY count DESC
        """)
        self._json(rows)

    def api_heatmap(self):
        rows = self._query("""
            SELECT DATE(run_at) as day, screen_name as screen,
                   ROUND(SUM(CASE WHEN result != 'passed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as rate
            FROM test_runs
            WHERE screen_name IS NOT NULL AND screen_name != ''
            GROUP BY day, screen
            HAVING COUNT(*) >= 2
            ORDER BY day, screen
        """)
        self._json(rows)

    def api_top_flakes(self):
        rows = self._query("""
            SELECT test_name, platform, screen_name, COUNT(*) as total,
                   SUM(CASE WHEN result != 'passed' THEN 1 ELSE 0 END) as fail_count,
                   (SELECT classification FROM test_runs t2
                    WHERE t2.test_name = t1.test_name AND t2.result != 'passed'
                    GROUP BY classification ORDER BY COUNT(*) DESC LIMIT 1
                   ) as common_classification
            FROM test_runs t1
            GROUP BY test_name, platform
            HAVING total >= 2
            ORDER BY fail_count * 1.0 / total DESC
            LIMIT 20
        """)
        self._json(rows)

    def api_devices(self):
        rows = self._query("""
            SELECT device_id, platform, COUNT(*) as total,
                   SUM(CASE WHEN result != 'passed' THEN 1 ELSE 0 END) as fail_count,
                   (SELECT classification FROM test_runs t2
                    WHERE t2.device_id = t1.device_id AND t2.result != 'passed'
                    GROUP BY classification ORDER BY COUNT(*) DESC LIMIT 1
                   ) as common_classification
            FROM test_runs t1
            GROUP BY device_id
            HAVING total >= 2
            ORDER BY fail_count * 1.0 / total DESC
        """)
        self._json(rows)

    def api_by_action(self):
        rows = self._query("""
            SELECT action_type,
                   COUNT(*) as total,
                   SUM(CASE WHEN result != 'passed' THEN 1 ELSE 0 END) as fail_count,
                   ROUND(SUM(CASE WHEN result != 'passed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as rate
            FROM test_runs
            WHERE action_type IS NOT NULL AND action_type != ''
            GROUP BY action_type
            ORDER BY rate DESC
        """)
        self._json(rows)

    def api_by_platform(self):
        rows = self._query("""
            SELECT platform,
                   COUNT(*) as total,
                   SUM(CASE WHEN result = 'passed' THEN 1 ELSE 0 END) as pass_count,
                   SUM(CASE WHEN result != 'passed' THEN 1 ELSE 0 END) as fail_count,
                   ROUND(SUM(CASE WHEN result != 'passed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as fail_rate
            FROM test_runs
            WHERE platform IS NOT NULL AND platform != ''
            GROUP BY platform
            ORDER BY fail_rate DESC
        """)
        self._json(rows)

    def api_volume(self):
        rows = self._query("""
            SELECT DATE(run_at) as day,
                   SUM(CASE WHEN result = 'passed' THEN 1 ELSE 0 END) as pass_count,
                   SUM(CASE WHEN result != 'passed' THEN 1 ELSE 0 END) as fail_count
            FROM test_runs
            GROUP BY day ORDER BY day
        """)
        self._json(rows)

    def api_duration_dist(self):
        rows = self._query("""
            SELECT
                CASE
                    WHEN duration_ms < 5000 THEN '0-5s'
                    WHEN duration_ms < 15000 THEN '5-15s'
                    WHEN duration_ms < 30000 THEN '15-30s'
                    WHEN duration_ms < 60000 THEN '30-60s'
                    WHEN duration_ms < 120000 THEN '60-120s'
                    ELSE '120s+'
                END as bucket,
                COUNT(*) as count
            FROM test_runs
            WHERE result != 'passed'
            GROUP BY bucket
            ORDER BY MIN(duration_ms)
        """)
        self._json(rows)

    def api_classification_trend(self):
        rows = self._query("""
            SELECT DATE(run_at) as day, classification, COUNT(*) as count
            FROM test_runs
            WHERE result != 'passed' AND classification IS NOT NULL
            GROUP BY day, classification
            ORDER BY day
        """)
        self._json(rows)

    def api_sessions(self):
        rows = self._query("""
            SELECT session_id, platform, device_id,
                   COUNT(*) as total_runs,
                   SUM(CASE WHEN result = 'passed' THEN 1 ELSE 0 END) as passed,
                   SUM(CASE WHEN result != 'passed' THEN 1 ELSE 0 END) as failed,
                   CAST(ROUND(AVG(duration_ms / 1000.0)) AS INTEGER) as avg_duration_s,
                   MIN(run_at) as first_run,
                   MAX(run_at) as last_run
            FROM test_runs
            WHERE session_id IS NOT NULL AND session_id != ''
            GROUP BY session_id
            ORDER BY last_run DESC
            LIMIT 20
        """)
        self._json(rows)

    def api_latest_session(self):
        session = self._query("""
            SELECT session_id, platform, device_id,
                   COUNT(*) as total_runs,
                   SUM(CASE WHEN result = 'passed' THEN 1 ELSE 0 END) as passed,
                   SUM(CASE WHEN result != 'passed' THEN 1 ELSE 0 END) as failed,
                   CAST(ROUND(AVG(duration_ms / 1000.0)) AS INTEGER) as avg_duration_s
            FROM test_runs
            WHERE session_id IS NOT NULL AND session_id != ''
            GROUP BY session_id
            ORDER BY MAX(run_at) DESC
            LIMIT 1
        """)
        if not session:
            self._json({"total_runs": 0, "passed": 0, "failed": 0})
            return
        s = session[0]
        tests = self._query("""
            SELECT test_name, result, duration_ms, platform, screen_name, classification
            FROM test_runs
            WHERE session_id = ?
            ORDER BY run_at
        """, (s["session_id"],))
        s["tests"] = tests
        self._json(s)

    def log_message(self, format, *args):
        pass


def main():
    global DB_PATH, PORT
    parser = argparse.ArgumentParser(description="FlakeIQ dashboard")
    parser.add_argument("--db", default=None, help="SQLite database path")
    parser.add_argument("--port", type=int, default=8080, help="HTTP port")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address")
    parser.add_argument("--seed", action="store_true", help="Use the seed database (flake-seed.db) instead of real data")
    parser.add_argument("--open", action="store_true", help="Open browser on start")
    args = parser.parse_args()
    if args.seed:
        seed_path = os.path.join(os.path.dirname(__file__), "flake-seed.db")
        if os.path.exists(seed_path):
            DB_PATH = seed_path
            print(f"Using seed database: {seed_path}")
        else:
            print("Seed database not found. Run 'python3 seed.py' first.")
            sys.exit(1)
    elif args.db:
        DB_PATH = args.db
    PORT = args.port
    os.environ["FLAKE_DB"] = DB_PATH

    if not os.path.exists(DB_PATH):
        print(f"Database not found: {DB_PATH}")
        print("Run 'python3 classify.py flake-results.jsonl' or 'python3 seed.py' first.")
        sys.exit(1)

    server = HTTPServer((args.host, PORT), Handler)
    url = f"http://{args.host}:{PORT}"
    print(f"FlakeIQ dashboard at {url}")
    if args.open:
        import webbrowser
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
