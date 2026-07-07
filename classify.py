#!/usr/bin/env python3
import json
import sqlite3
import sys
import os
import argparse
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError

DB_PATH = os.environ.get("FLAKE_DB", "flake.db")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")

CLASSIFICATION_PROMPT = """You are a test failure classifier. Given a mobile E2E test failure, classify it into exactly one category.

Categories:
- REAL_BUG: the app behavior is wrong (element missing, wrong UI state, crash, assertion failure)
- TIMEOUT_FLAKE: action timed out but the element typically appears eventually (race condition, slow render)
- DEVICE_FLAKE: device/emulator issue (connection lost, ANR dialog, memory pressure, "could not verify foreground")
- LOCATOR_FLAKE: element found but not visible/interactable, scrollIntoViewIfNeeded failed, stale element
- UNKNOWN: can't determine from the given information

Reply with ONLY the category name and a one-sentence reason separated by "|".
Example: "TIMEOUT_FLAKE|actionTimeout exceeded on fill, element appeared on retry"

---
Test: {test_name}
Platform: {platform}
Error: {error_message}
Last actions: {last_actions}
"""

SCHEMA = """
CREATE TABLE IF NOT EXISTS test_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_file TEXT,
    test_name TEXT,
    platform TEXT,
    device_id TEXT,
    duration_ms INTEGER,
    result TEXT,
    error_message TEXT,
    last_actions TEXT,
    classification TEXT,
    classification_reason TEXT,
    screen_name TEXT,
    action_type TEXT,
    session_id TEXT,
    run_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_run_at ON test_runs(run_at);
CREATE INDEX IF NOT EXISTS idx_screen ON test_runs(screen_name);
CREATE INDEX IF NOT EXISTS idx_result ON test_runs(result);
"""


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript(SCHEMA)
    db.commit()
    return db


def classify_failure(record: dict) -> tuple[str | None, str | None]:
    prompt = CLASSIFICATION_PROMPT.format(
        test_name=record["test_name"],
        platform=record.get("platform", "unknown"),
        error_message=record.get("error_message", "")[:2000],
        last_actions=json.dumps(record.get("last_actions", [])),
    )
    payload = json.dumps({"model": MODEL, "prompt": prompt, "stream": False}).encode()
    req = Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})
    try:
        resp = urlopen(req, timeout=30)
        body = json.loads(resp.read())
        text = body.get("response", "").strip()
        if "|" in text:
            cat, reason = text.split("|", 1)
            cat = cat.strip().upper()
            if cat in ("REAL_BUG", "TIMEOUT_FLAKE", "DEVICE_FLAKE", "LOCATOR_FLAKE", "UNKNOWN"):
                return cat, reason.strip()
        return "UNKNOWN", f"Could not parse: {text[:200]}"
    except URLError as e:
        print(f"  [warn] Ollama unavailable ({e.reason}), skipping classification")
        return None, None
    except Exception as e:
        print(f"  [warn] Classification failed: {e}")
        return None, None


def guess_action_type(last_actions: list[str]) -> str:
    for action in reversed(last_actions):
        al = action.lower()
        if "fill" in al: return "fill"
        if "tap" in al or "click" in al: return "tap"
        if "swipe" in al or "scroll" in al: return "swipe"
        if "scrollintoview" in al: return "scrollIntoView"
        if "press" in al: return "press"
    return "other"


def process_jsonl(jsonl_path: str, db: sqlite3.Connection):
    count = 0
    classified = 0
    skipped = 0
    cursor = db.cursor()

    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            count += 1

            # detect duplicate by test_name + run_at
            cursor.execute(
                "SELECT id FROM test_runs WHERE test_name=? AND run_at=?",
                (record["test_name"], record["run_at"]),
            )
            if cursor.fetchone():
                skipped += 1
                continue

            action_type = guess_action_type(record.get("last_actions", []))

            if record["result"] != "passed":
                cat, reason = classify_failure(record)
                if cat:
                    classified += 1
                    record["classification"] = cat
                    record["classification_reason"] = reason
            else:
                record["classification"] = None
                record["classification_reason"] = None

            cursor.execute(
                """INSERT INTO test_runs
                   (test_file, test_name, platform, device_id, duration_ms, result,
                    error_message, last_actions, classification, classification_reason,
                    screen_name, action_type, session_id, run_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    record.get("test_file"),
                    record["test_name"],
                    record.get("platform"),
                    record.get("device_id"),
                    record.get("duration_ms"),
                    record["result"],
                    record.get("error_message", ""),
                    json.dumps(record.get("last_actions", [])),
                    record.get("classification"),
                    record.get("classification_reason"),
                    record.get("screen_name"),
                    action_type,
                    record.get("session_id"),
                    record["run_at"],
                ),
            )

    db.commit()
    print(f"Processed: {count} records ({classified} classified, {skipped} skipped duplicates)")


def main():
    parser = argparse.ArgumentParser(description="FlakeIQ: classify test failures and store in SQLite")
    parser.add_argument("jsonl", nargs="?", default="flake-results.jsonl",
                        help="Path to JSONL file from flake-reporter.ts")
    parser.add_argument("--db", default=DB_PATH, help="SQLite database path")
    parser.add_argument("--ollama-url", default=OLLAMA_URL, help="Ollama API URL")
    parser.add_argument("--model", default=MODEL, help="Ollama model name")
    args = parser.parse_args()

    os.environ["FLAKE_DB"] = args.db
    os.environ["OLLAMA_URL"] = args.ollama_url
    os.environ["OLLAMA_MODEL"] = args.model

    if not os.path.exists(args.jsonl):
        print(f"JSONL file not found: {args.jsonl}")
        sys.exit(1)

    db = init_db()
    process_jsonl(args.jsonl, db)
    db.close()


if __name__ == "__main__":
    main()
