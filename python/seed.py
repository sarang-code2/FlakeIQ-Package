#!/usr/bin/env python3
import sqlite3
import json
import os
import random
import sys
from datetime import datetime, timedelta

DB_PATH = os.environ.get("FLAKE_DB", "flake.db")
random.seed(42)

SCREENS = ["login", "profile", "form", "list", "alert", "animation", "calendar", "gesture", "media", "signature", "home"]
DEVICES = [
    ("Medium_Phone_API_36.0", "android"),
    ("emulator-5554", "android"),
    ("iPhone_16_Pro_iOS_18", "ios"),
    ("iPhone_15_iOS_17", "ios"),
]

TESTS = [
    # (test_file, test_name, screen)
    ("tests/example.spec.ts", "login flow - fill form and submit", "login"),
    ("tests/example.spec.ts", "login flow - invalid credentials shows error", "login"),
    ("tests/profile.spec.ts", "edit profile - change name and save", "profile"),
    ("tests/profile.spec.ts", "toggle notification switches", "profile"),
    ("tests/profile.spec.ts", "logout from profile screen", "profile"),
    ("tests/forms.spec.ts", "fill all form fields and submit", "form"),
    ("tests/forms.spec.ts", "form validation shows errors", "form"),
    ("tests/lists.spec.ts", "scroll through list items", "list"),
    ("tests/lists.spec.ts", "pull to refresh list", "list"),
    ("tests/alerts.spec.ts", "show and dismiss alert dialog", "alert"),
    ("tests/alerts.spec.ts", "alert with multiple buttons", "alert"),
    ("tests/animation.spec.ts", "animated element appears", "animation"),
    ("tests/calendar.spec.ts", "select date from calendar", "calendar"),
    ("tests/gestures.spec.ts", "swipe between tabs", "gesture"),
    ("tests/media.spec.ts", "pick image from gallery", "media"),
    ("tests/signature.spec.ts", "draw and save signature", "signature"),
    ("tests/home.spec.ts", "home screen loads correctly", "home"),
]

ACTION_TEMPLATES = {
    "login": [
        ["tap(#emailInput)", "fill(#emailInput)", "tap(#passwordInput)", "fill(#passwordInput)", "tap(#loginButton)"],
        ["tap(#emailInput)", "fill(#emailInput)", "tap(#passwordInput)", "fill(#passwordInput)", "tap(#loginButton)", "waitFor(#homeScreen)"],
        ["tap(#emailInput)", "fill(#emailInput)", "tap(#passwordInput)", "fill(#passwordInput)", "tap(#loginButton)", "waitForText(Invalid)"],
    ],
    "profile": [
        ["tap(#navProfile)", "waitFor(#profileScreen)", "tap(#editButton)", "fill(#nameInput)", "tap(#saveButton)", "waitForText(Profile updated)"],
        ["tap(#navProfile)", "waitFor(#profileScreen)", "swipe('up')", "tap(#notificationsSwitch)", "waitForText(Saved)"],
        ["tap(#navProfile)", "waitFor(#profileScreen)", "swipe('up')", "tap(#logoutButton)", "waitFor(#loginScreen)"],
    ],
    "form": [
        ["tap(#navFormControls)", "waitFor(#formScreen)", "fill(#textInput)", "fill(#emailField)", "fill(#phoneField)", "tap(#submitButton)"],
        ["tap(#navFormControls)", "waitFor(#formScreen)", "tap(#submitButton)", "waitForText(required)"],
    ],
    "list": [
        ["tap(#navListsDemo)", "waitFor(#listScreen)", "swipe('up')", "swipe('up')", "tap(#listItem_5)"],
        ["tap(#navListsDemo)", "waitFor(#listScreen)", "swipe('down')", "waitForText(Item 1)"],
    ],
    "alert": [
        ["tap(#navAlertsDemo)", "waitFor(#alertScreen)", "tap(#showAlertButton)", "waitForText(OK)", "tap(#okButton)"],
        ["tap(#navAlertsDemo)", "waitFor(#alertScreen)", "tap(#multiButtonAlert)", "tap(#cancelButton)"],
    ],
    "animation": [
        ["tap(#navAnimationDemo)", "waitFor(#animationScreen)", "tap(#startAnimation)", "waitForText(Animation complete)"],
    ],
    "calendar": [
        ["tap(#navCalendarDemo)", "waitFor(#calendarScreen)", "tap(#datePicker)", "tap(#day15)", "tap(#confirmButton)"],
    ],
    "gesture": [
        ["tap(#navGesturesDemo)", "waitFor(#gestureScreen)", "swipe('left')", "waitForText(Tab 2)"],
    ],
    "media": [
        ["tap(#navMediaDemo)", "waitFor(#mediaScreen)", "tap(#pickImageButton)", "waitForText(Image selected)"],
    ],
    "signature": [
        ["tap(#navSignatureDemo)", "waitFor(#signatureScreen)", "draw(#canvas)", "tap(#saveSignature)", "waitForText(Signature saved)"],
    ],
    "home": [
        ["waitFor(#homeScreen)", "waitForText(Welcome)", "verify card list visible"],
    ],
}

ERROR_TEMPLATES = {
    "passed": (None, None),
    "timedOut": [
        ("actionTimeout 20000ms exceeded", "TIMEOUT_FLAKE", "action timed out waiting for element to appear, likely slow render"),
        ("Timeout 30000ms exceeded while waiting for #element", "TIMEOUT_FLAKE", "element took longer than expected to become visible"),
        ("Test timeout of 120000ms exceeded", "TIMEOUT_FLAKE", "full test timeout exceeded, possible memory pressure slow-down"),
    ],
    "failed": [
        ("ExpectError: Expected 1, but received 0", "LOCATOR_FLAKE", "element not found in tree, race condition on navigation"),
        ("ExpectError: Expected value to be truthy, but received false", "REAL_BUG", "UI state did not match expected value, possible regression"),
        ("Error: element is not visible", "LOCATOR_FLAKE", "element found but not interactable, viewport calculation mismatch"),
        ("Error: Method not found", "DEVICE_FLAKE", "device connection lost during action, RPC failure"),
        ("Error: Could not verify foreground activity", "DEVICE_FLAKE", "ANR dialog or system overlay blocking the app"),
        ("Error: fill failed - element detached from DOM", "LOCATOR_FLAKE", "stale element reference after navigation"),
        ("ExpectError: Expected 'Profile updated' but received 'Error saving'", "REAL_BUG", "app returned error state instead of success"),
    ],
}


def generate_last_actions(screen: str, result: str) -> list[str]:
    templates = ACTION_TEMPLATES.get(screen, [["tap(#generic)", "waitFor(#generic)"]])
    base = random.choice(templates)
    if result == "passed":
        return base
    # For failures, return a prefix of actions (the last few before crash)
    cut = random.randint(1, len(base))
    return base[:cut]


def generate_run_at(base_date: datetime, day_offset: int) -> str:
    day = base_date + timedelta(days=day_offset)
    hour = random.randint(7, 22)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return day.replace(hour=hour, minute=minute, second=second).isoformat()


def generate_failure_rate(screen: str, platform: str) -> float:
    rates = {
        "login": {"android": 0.15, "ios": 0.05},
        "profile": {"android": 0.12, "ios": 0.04},
        "form": {"android": 0.08, "ios": 0.03},
        "list": {"android": 0.20, "ios": 0.06},
        "alert": {"android": 0.10, "ios": 0.04},
        "animation": {"android": 0.18, "ios": 0.07},
        "calendar": {"android": 0.08, "ios": 0.03},
        "gesture": {"android": 0.22, "ios": 0.08},
        "media": {"android": 0.25, "ios": 0.10},
        "signature": {"android": 0.15, "ios": 0.06},
        "home": {"android": 0.05, "ios": 0.02},
    }
    return rates.get(screen, {}).get(platform, 0.10)


def seed_database(db_path: str, num_days: int = 30, runs_per_day: int = 5):
    db = sqlite3.connect(db_path)
    db.executescript("""
        DROP TABLE IF EXISTS test_runs;
        CREATE TABLE test_runs (
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
        CREATE INDEX IF NOT EXISTS idx_platform ON test_runs(platform);
    """)
    cursor = db.cursor()

    base_date = datetime.now() - timedelta(days=num_days)
    total = 0
    passed = 0
    failed = 0

    for day in range(num_days):
        # run all test files on each day, some multiple times
        for test_file, test_name, screen in TESTS:
            for platform_id in [0, 1]:  # 0=android, 1=ios
                device_id, platform = DEVICES[platform_id]
                failure_rate = generate_failure_rate(screen, platform)

                for run_num in range(runs_per_day):
                    # Determine result
                    is_flake = random.random() < failure_rate

                    if is_flake:
                        # For flakes, sometimes retry succeeds
                        is_retry = random.random() < 0.4
                        if is_retry:
                            # retry passed after initial failure
                            result = "passed"
                            error_msg = None
                            classification = None
                            classification_reason = None
                            passed += 1
                        else:
                            result = random.choice(["timedOut", "failed"])
                            failed += 1
                    else:
                        result = "passed"
                        error_msg = None
                        classification = None
                        classification_reason = None
                        passed += 1

                    # Determine duration
                    if result == "timedOut":
                        duration_ms = random.randint(60000, 180000)
                    elif result == "failed":
                        duration_ms = random.randint(10000, 55000)
                    else:
                        duration_ms = random.randint(3000, 25000)

                    # Error message and classification
                    if result == "passed":
                        error_msg = ""
                        classification = None
                        classification_reason = None
                        last_actions = generate_last_actions(screen, "passed")
                    else:
                        error_opts = ERROR_TEMPLATES[result]
                        error_msg, classification, classification_reason = random.choice(error_opts)
                        last_actions = generate_last_actions(screen, "failed")

                    # Determine action_type from last actions
                    action_type = "other"
                    for action in reversed(last_actions):
                        al = action.lower()
                        if "fill" in al: action_type = "fill"; break
                        if "tap" in al or "click" in al: action_type = "tap"; break
                        if "swipe" in al or "scroll" in al: action_type = "swipe"; break
                        if "scrollintoview" in al: action_type = "scrollIntoView"; break
                        if "press" in al: action_type = "press"; break

                    cursor.execute(
                        """INSERT INTO test_runs
                           (test_file, test_name, platform, device_id, duration_ms, result,
                            error_message, last_actions, classification, classification_reason,
                            screen_name, action_type, session_id, run_at)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            test_file, test_name, platform, device_id,
                            duration_ms, result, error_msg,
                            json.dumps(last_actions), classification,
                            classification_reason, screen, action_type,
                            f"{device_id}_{day}",
                            generate_run_at(base_date, day),
                        ),
                    )
                    total += 1

    db.commit()
    db.close()
    print(f"Seeded {total} test runs ({passed} passed, {failed} failed)")
    print(f"Overall pass rate: {passed/total*100:.1f}%")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else DB_PATH
    seed_database(path)
