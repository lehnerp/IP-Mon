import json
import logging
import math
import os
import sys
import smtplib
import re
import shutil
import socket
import sqlite3
import ssl
import subprocess
import threading
import time
import urllib.error
import urllib.request
import urllib.parse
import http.client
from concurrent.futures import ThreadPoolExecutor, wait as futures_wait
from collections import defaultdict, deque
from contextlib import closing
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from email.message import EmailMessage
from pathlib import Path

import base64
import csv
import hmac
import io
import platform

from flask import Flask, Response, jsonify, render_template, request

APP_VERSION = "6.0"
IS_WINDOWS = platform.system().lower().startswith("win")
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = Path(os.environ.get("IPMON_CONFIG") or (BASE_DIR / "config.json")).resolve()
STARTER_CONFIG = {
    "listen_host": "0.0.0.0",
    "listen_port": 8096,
    "database": "monitor.db",
    "groups": ["Local", "Internet"],
    "targets": [
        {"name": "This computer", "host": "127.0.0.1", "group": "Local"},
        {"name": "Cloudflare DNS", "host": "1.1.1.1", "group": "Internet"},
        {"name": "Google DNS", "host": "8.8.8.8", "group": "Internet"},
        {"name": "Cloudflare web", "url": "https://www.cloudflare.com/", "group": "Internet"},
    ],
}
if not CONFIG_PATH.exists():
    # First start: create a working configuration so the monitor runs immediately.
    # Real targets are then added in the dashboard (Settings -> Targets & Groups).
    CONFIG_PATH.write_text(json.dumps(STARTER_CONFIG, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Created {CONFIG_PATH} with starter targets - edit them in the dashboard under Settings.")
try:
    CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
except json.JSONDecodeError as exc:
    raise SystemExit(f"{CONFIG_PATH.name} is not valid JSON: line {exc.lineno}, column {exc.colno}: {exc.msg}")
if not isinstance(CONFIG, dict):
    raise SystemExit(f"{CONFIG_PATH.name} must contain a JSON object")
config_lock = threading.RLock()

CONFIG_DEFAULTS = {
    "listen_host": "0.0.0.0",
    "listen_port": 8096,
    "database": "monitor.db",
    "poll_interval_seconds": 2,
    "sample_interval_seconds": 10,
    "ping_timeout_seconds": 1.5,
    "http_timeout_seconds": 5,
    "history_retention_days": 30,
    "event_retention_days": 365,
    "ui": {"language": "en"},
    "monitoring": {
        "startup_reconciliation": True,
        "startup_success_checks": 2,
        "startup_failure_checks": 3,
        "startup_alert_grace_seconds": 30,
        "startup_stale_after_seconds": 60,
        "path_health_enabled": True,
        "path_health_interval_seconds": 300,
        "path_health_burst_packets": 8,
        "path_health_timeout_seconds": 8,
        "path_health_loss_watch_percent": 5,
        "path_health_loss_critical_percent": 20,
        "path_health_jitter_watch_ms": 5,
        "path_health_baseline_ratio_watch": 2.5,
        "failure_window_checks": 5,
        "failure_threshold": 3,
        "recovery_success_threshold": 3,
        "baseline_enabled": True,
        "baseline_time_constant_hours": 6,
        "baseline_min_samples": 30,
        "anomaly_elevated_z": 2.5,
        "anomaly_high_z": 4.0,
        "anomaly_severe_z": 6.0,
        "tls_expiry_warning_days": 30,
        "flapping_window_seconds": 900,
        "flapping_transition_threshold": 4
    },
    "email_alerts": {
        "enabled": False,
        "degradation_seconds": 180,
        "recovery_seconds": 60,
        "statistics_window_seconds": 180,
        "health_score_below": 55,
        "availability_below": 99.0,
        "latency_above_ms": 100,
        "jitter_above_ms": 30,
        "http_latency_above_ms": 1000,
        "http_jitter_above_ms": 300,
        "offline": True,
        "send_recovery": True,
        "reminder_seconds": 0,
        "minimum_failed_checks": 3,
        "alert_on_flapping": True,
        "escalation_seconds": 900
    }
}

def _merge_missing(dst, defaults):
    changed = False
    for key, value in defaults.items():
        if key not in dst:
            dst[key] = json.loads(json.dumps(value))
            changed = True
        elif isinstance(value, dict) and isinstance(dst.get(key), dict):
            changed = _merge_missing(dst[key], value) or changed
    return changed

def _write_config_atomic(config):
    tmp = CONFIG_PATH.with_suffix(CONFIG_PATH.suffix + ".tmp")
    bak = CONFIG_PATH.with_suffix(CONFIG_PATH.suffix + ".bak")
    payload = json.dumps(config, indent=2, ensure_ascii=False) + "\n"
    # Write and fsync through the same writable handle. (fsync on a read-only
    # handle fails with EBADF on Windows.)
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(payload)
        fh.flush()
        try:
            os.fsync(fh.fileno())
        except OSError:
            pass  # durability is best-effort; never block startup on it
    if CONFIG_PATH.exists():
        try:
            shutil.copy2(CONFIG_PATH, bak)
        except Exception:
            logging.exception("Could not update config backup")
    # On Windows an editor, antivirus or indexer may briefly lock config.json.
    for attempt in range(10):
        try:
            os.replace(tmp, CONFIG_PATH)
            return
        except PermissionError:
            if attempt == 9:
                raise
            time.sleep(0.2)

if _merge_missing(CONFIG, CONFIG_DEFAULTS):
    try:
        _write_config_atomic(CONFIG)
    except Exception as exc:
        # Defaults are still applied in memory; only the file update is skipped.
        print(f"WARNING: could not add new default settings to {CONFIG_PATH.name}: {exc}", file=sys.stderr)

DB_PATH = BASE_DIR / CONFIG.get("database", "monitor.db")
POLL_INTERVAL = float(CONFIG.get("poll_interval_seconds", 2))
PING_TIMEOUT = float(CONFIG.get("ping_timeout_seconds", 1.5))
HTTP_TIMEOUT = float(CONFIG.get("http_timeout_seconds", 5))
LISTEN_HOST = CONFIG.get("listen_host", "0.0.0.0")
LISTEN_PORT = int(CONFIG.get("listen_port", 8096))
RETENTION_DAYS = int(CONFIG.get("history_retention_days", 30))
EVENT_RETENTION_DAYS = max(RETENTION_DAYS, int(CONFIG.get("event_retention_days", 365)))
SAMPLE_INTERVAL = max(POLL_INTERVAL, float(CONFIG.get("sample_interval_seconds", 10)))
TARGETS = CONFIG.get("targets", [])
EMAIL_ALERTS = CONFIG.get("email_alerts", {})
ALERTS_ENABLED = bool(EMAIL_ALERTS.get("enabled", False))
ALERT_DEGRADATION_SECONDS = int(EMAIL_ALERTS.get("degradation_seconds", 180))
ALERT_RECOVERY_SECONDS = int(EMAIL_ALERTS.get("recovery_seconds", 60))
ALERT_REMINDER_SECONDS = int(EMAIL_ALERTS.get("reminder_seconds", 0))
MONITORING = CONFIG.get("monitoring", {}) or {}
DEFAULT_FAILURE_WINDOW = max(3, int(MONITORING.get("failure_window_checks", 5)))
DEFAULT_FAILURE_THRESHOLD = max(1, int(MONITORING.get("failure_threshold", 3)))
DEFAULT_RECOVERY_THRESHOLD = max(1, int(MONITORING.get("recovery_success_threshold", 3)))
BASELINE_ENABLED = bool(MONITORING.get("baseline_enabled", True))
BASELINE_TAU_SECONDS = max(300.0, float(MONITORING.get("baseline_time_constant_hours", 6)) * 3600.0)
BASELINE_MIN_SAMPLES = max(5, int(MONITORING.get("baseline_min_samples", 30)))

app = Flask(__name__)
stop_event = threading.Event()
db_write_lock = threading.Lock()
alert_lock = threading.Lock()
stats_lock = threading.Lock()
# Fast in-memory rolling statistics. This keeps /api/status and alert evaluation
# independent of the potentially multi-million-row raw samples table.
rolling_minutes = defaultdict(lambda: deque(maxlen=1500))
current_minute = {}
recent_checks = defaultdict(deque)
last_sample_persist = {}
alert_runtime = {}
stability_runtime = {}
baseline_runtime = {}
current_diagnostics = {}
latest_target_state = {}
flap_runtime = defaultdict(deque)
flap_active = {}
state_runtime_lock = threading.Lock()
flap_lock = threading.Lock()
stability_lock = threading.Lock()
baseline_lock = threading.Lock()
startup_lock = threading.Lock()
startup_started_at = time.time()
startup_runtime = {}
persisted_effective_state = {}
startup_complete = False
path_health_lock = threading.Lock()
path_health_runtime = {}
path_health_history = defaultdict(lambda: deque(maxlen=288))
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def apply_runtime_config():
    global POLL_INTERVAL, PING_TIMEOUT, HTTP_TIMEOUT, RETENTION_DAYS, SAMPLE_INTERVAL, EVENT_RETENTION_DAYS
    global EMAIL_ALERTS, ALERTS_ENABLED, ALERT_DEGRADATION_SECONDS, ALERT_RECOVERY_SECONDS, ALERT_REMINDER_SECONDS
    global MONITORING, DEFAULT_FAILURE_WINDOW, DEFAULT_FAILURE_THRESHOLD, DEFAULT_RECOVERY_THRESHOLD
    global BASELINE_ENABLED, BASELINE_TAU_SECONDS, BASELINE_MIN_SAMPLES
    POLL_INTERVAL = max(0.2, float(CONFIG.get("poll_interval_seconds", 2)))
    PING_TIMEOUT = max(0.1, float(CONFIG.get("ping_timeout_seconds", 1.5)))
    HTTP_TIMEOUT = max(0.2, float(CONFIG.get("http_timeout_seconds", 5)))
    RETENTION_DAYS = max(1, int(CONFIG.get("history_retention_days", 30)))
    EVENT_RETENTION_DAYS = max(RETENTION_DAYS, int(CONFIG.get("event_retention_days", 365)))
    SAMPLE_INTERVAL = max(POLL_INTERVAL, float(CONFIG.get("sample_interval_seconds", 10)))
    EMAIL_ALERTS = CONFIG.get("email_alerts", {}) or {}
    ALERTS_ENABLED = bool(EMAIL_ALERTS.get("enabled", False))
    ALERT_DEGRADATION_SECONDS = int(EMAIL_ALERTS.get("degradation_seconds", 180))
    ALERT_RECOVERY_SECONDS = int(EMAIL_ALERTS.get("recovery_seconds", 60))
    ALERT_REMINDER_SECONDS = int(EMAIL_ALERTS.get("reminder_seconds", 0))
    MONITORING = CONFIG.get("monitoring", {}) or {}
    DEFAULT_FAILURE_WINDOW = max(3, int(MONITORING.get("failure_window_checks", 5)))
    DEFAULT_FAILURE_THRESHOLD = max(1, int(MONITORING.get("failure_threshold", 3)))
    DEFAULT_RECOVERY_THRESHOLD = max(1, int(MONITORING.get("recovery_success_threshold", 3)))
    BASELINE_ENABLED = bool(MONITORING.get("baseline_enabled", True))
    BASELINE_TAU_SECONDS = max(300.0, float(MONITORING.get("baseline_time_constant_hours", 6)) * 3600.0)
    BASELINE_MIN_SAMPLES = max(5, int(MONITORING.get("baseline_min_samples", 30)))



def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def db_connect():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def ensure_column(conn, table, column, definition):
    cols = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db():
    with closing(db_connect()) as conn:
        conn.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS target_state (
          target TEXT PRIMARY KEY,
          host TEXT NOT NULL,
          tcp_port INTEGER,
          observed_at TEXT,
          online INTEGER DEFAULT 0,
          ping_ok INTEGER DEFAULT 0,
          tcp_ok INTEGER,
          latency_ms REAL,
          last_error TEXT,
          consecutive_failures INTEGER DEFAULT 0,
          total_checks INTEGER DEFAULT 0,
          total_failures INTEGER DEFAULT 0,
          total_state_changes INTEGER DEFAULT 0,
          first_observed_at TEXT,
          last_online_at TEXT,
          last_offline_at TEXT,
          check_kind TEXT DEFAULT 'host',
          http_status INTEGER,
          verify_ssl INTEGER,
          dns_ms REAL,
          tcp_connect_ms REAL,
          tls_ms REAL,
          server_response_ms REAL,
          raw_ok INTEGER DEFAULT 0,
          stability_confirmed INTEGER DEFAULT 1,
          failure_window_checks INTEGER DEFAULT 0,
          failure_window_failures INTEGER DEFAULT 0,
          baseline_latency_ms REAL,
          baseline_variance REAL DEFAULT 0,
          baseline_samples INTEGER DEFAULT 0,
          anomaly_z REAL,
          anomaly_level TEXT,
          tls_expires_at TEXT,
          tls_days_left REAL,
          maintenance_active INTEGER DEFAULT 0,
          maintenance_label TEXT
        );
        CREATE TABLE IF NOT EXISTS samples (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          target TEXT NOT NULL,
          observed_at TEXT NOT NULL,
          online INTEGER NOT NULL,
          latency_ms REAL,
          ping_ok INTEGER NOT NULL,
          tcp_ok INTEGER,
          error TEXT,
          check_kind TEXT DEFAULT 'host',
          http_status INTEGER,
          dns_ms REAL,
          tcp_connect_ms REAL,
          tls_ms REAL,
          server_response_ms REAL,
          maintenance INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_samples_target_time ON samples(target, observed_at DESC);
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          target TEXT NOT NULL,
          observed_at TEXT NOT NULL,
          category TEXT NOT NULL,
          detail TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_events_time ON events(observed_at DESC);
        CREATE TABLE IF NOT EXISTS alert_state (
          target TEXT PRIMARY KEY,
          condition_active INTEGER DEFAULT 0,
          condition_since TEXT,
          alert_sent INTEGER DEFAULT 0,
          alerted_at TEXT,
          recovering_since TEXT,
          last_reminder_at TEXT,
          last_reason TEXT,
          last_score INTEGER,
          last_metrics TEXT,
          escalated_at TEXT
        );
        """)
        # Upgrade databases created by older versions in place.
        ensure_column(conn, "target_state", "check_kind", "TEXT DEFAULT 'host'")
        ensure_column(conn, "target_state", "http_status", "INTEGER")
        ensure_column(conn, "target_state", "verify_ssl", "INTEGER")
        ensure_column(conn, "samples", "check_kind", "TEXT DEFAULT 'host'")
        ensure_column(conn, "samples", "http_status", "INTEGER")
        ensure_column(conn, "target_state", "dns_ms", "REAL")
        ensure_column(conn, "target_state", "tcp_connect_ms", "REAL")
        ensure_column(conn, "target_state", "tls_ms", "REAL")
        ensure_column(conn, "target_state", "server_response_ms", "REAL")
        ensure_column(conn, "samples", "dns_ms", "REAL")
        ensure_column(conn, "samples", "tcp_connect_ms", "REAL")
        ensure_column(conn, "samples", "tls_ms", "REAL")
        ensure_column(conn, "samples", "server_response_ms", "REAL")
        ensure_column(conn, "target_state", "raw_ok", "INTEGER DEFAULT 0")
        ensure_column(conn, "target_state", "stability_confirmed", "INTEGER DEFAULT 1")
        ensure_column(conn, "target_state", "failure_window_checks", "INTEGER DEFAULT 0")
        ensure_column(conn, "target_state", "failure_window_failures", "INTEGER DEFAULT 0")
        ensure_column(conn, "target_state", "baseline_latency_ms", "REAL")
        ensure_column(conn, "target_state", "baseline_variance", "REAL DEFAULT 0")
        ensure_column(conn, "target_state", "baseline_samples", "INTEGER DEFAULT 0")
        ensure_column(conn, "target_state", "anomaly_z", "REAL")
        ensure_column(conn, "target_state", "anomaly_level", "TEXT")
        ensure_column(conn, "target_state", "tls_expires_at", "TEXT")
        ensure_column(conn, "target_state", "tls_days_left", "REAL")
        ensure_column(conn, "target_state", "maintenance_active", "INTEGER DEFAULT 0")
        ensure_column(conn, "target_state", "maintenance_label", "TEXT")
        ensure_column(conn, "samples", "maintenance", "INTEGER DEFAULT 0")
        ensure_column(conn, "alert_state", "escalated_at", "TEXT")
        conn.commit()


def target_url(target):
    url = target.get("url")
    host = target.get("host")
    if url:
        return str(url)
    if isinstance(host, str) and host.lower().startswith(("http://", "https://")):
        return host
    return None


def target_display(target):
    return target_url(target) or str(target.get("host", ""))


def validate_targets():
    names = set()
    for i, target in enumerate(TARGETS, start=1):
        if not isinstance(target, dict):
            raise SystemExit(f"Target #{i} must be a JSON object")
        name = str(target.get("name", "")).strip()
        if not name:
            raise SystemExit(f"Target #{i} is missing 'name'")
        if name in names:
            raise SystemExit(f"Duplicate target name: {name}")
        names.add(name)
        if not target_url(target) and not target.get("host"):
            raise SystemExit(f"Target '{name}' needs 'host' or 'url'")

    graph = {}
    for target in TARGETS:
        name = target["name"]
        deps = target.get("depends_on", [])
        if isinstance(deps, str):
            deps = [deps]
        deps = [str(x).strip() for x in deps if str(x).strip()]
        for dep in deps:
            if dep not in names:
                raise SystemExit(f"Target '{name}' depends on unknown target '{dep}'")
            if dep == name:
                raise SystemExit(f"Target '{name}' cannot depend on itself")
        graph[name] = deps

    visiting, done = set(), set()
    def visit(node):
        if node in visiting:
            raise SystemExit(f"Dependency cycle detected at '{node}'")
        if node in done:
            return
        visiting.add(node)
        for dep in graph.get(node, []):
            visit(dep)
        visiting.remove(node)
        done.add(node)
    for node in graph:
        visit(node)

WEEKDAY_ALIASES = {
    "mon":0,"monday":0,"po":0,"pondeli":0,"pondělí":0,
    "tue":1,"tuesday":1,"ut":1,"út":1,"utery":1,"úterý":1,
    "wed":2,"wednesday":2,"st":2,"streda":2,"středa":2,
    "thu":3,"thursday":3,"ct":3,"čt":3,"ctvrtek":3,"čtvrtek":3,
    "fri":4,"friday":4,"pa":4,"pá":4,"patek":4,"pátek":4,
    "sat":5,"saturday":5,"so":5,"sobota":5,
    "sun":6,"sunday":6,"ne":6,"nedele":6,"neděle":6,
}

def _parse_hhmm(value):
    try:
        h, m = str(value).strip().split(":", 1)
        h, m = int(h), int(m)
        if 0 <= h <= 23 and 0 <= m <= 59:
            return h * 60 + m
    except Exception:
        pass
    return None

def maintenance_status(target, at=None):
    """Return (active, label). Supports weekly windows and one-time ISO ranges."""
    cfg = target.get("maintenance")
    if not cfg:
        return False, None
    if isinstance(cfg, dict):
        if cfg.get("enabled") is False:
            return False, None
        windows = cfg.get("windows", [])
        default_label = cfg.get("label")
        default_tz = cfg.get("timezone")
    elif isinstance(cfg, list):
        windows, default_label, default_tz = cfg, None, None
    else:
        return False, None

    now = at or datetime.now(timezone.utc).astimezone()
    for window in windows:
        if not isinstance(window, dict) or window.get("enabled") is False:
            continue
        tz_name = window.get("timezone") or default_tz
        local_now = now
        if tz_name:
            try:
                local_now = now.astimezone(ZoneInfo(str(tz_name)))
            except Exception:
                logging.warning("Unknown maintenance timezone %r for %s", tz_name, target["name"])

        # One-time absolute range.
        once_start = parse_iso(window.get("from") or window.get("start_at"))
        once_end = parse_iso(window.get("to") or window.get("end_at"))
        if once_start and once_end:
            try:
                if once_start <= local_now <= once_end:
                    return True, str(window.get("label") or default_label or "Scheduled maintenance")
            except TypeError:
                pass

        start = _parse_hhmm(window.get("start"))
        end = _parse_hhmm(window.get("end"))
        if start is None or end is None:
            continue
        days = window.get("days")
        if days:
            if isinstance(days, str):
                days = [days]
            allowed = {WEEKDAY_ALIASES.get(str(x).strip().lower()) for x in days}
            allowed.discard(None)
            # For overnight windows, early-morning portion belongs to previous day's window.
            minute = local_now.hour * 60 + local_now.minute
            day = local_now.weekday()
            if end <= start and minute < end:
                day = (day - 1) % 7
            if day not in allowed:
                continue
        minute = local_now.hour * 60 + local_now.minute
        active = start <= minute < end if end > start else (minute >= start or minute < end)
        if active:
            return True, str(window.get("label") or default_label or "Scheduled maintenance")
    return False, None

def stability_snapshot(target, raw_ok):
    """Hold confirmed outage state during maintenance without feeding the debounce window."""
    name = target["name"]
    with stability_lock:
        st = stability_runtime.setdefault(name, {"state": None, "confirmed": False, "window": deque()})
        w = st["window"]
        failures = sum(1 for x in w if not x)
        effective = bool(raw_ok) if st["state"] is None else bool(st["state"])
        return effective, bool(st["confirmed"]), None, len(w), failures

def dependency_blockers(target):
    deps = target.get("depends_on", [])
    if isinstance(deps, str):
        deps = [deps]
    blockers = []
    with state_runtime_lock:
        snapshot = dict(latest_target_state)
    for dep in deps:
        dep = str(dep).strip()
        st = snapshot.get(dep)
        if not st:
            continue
        if st.get("maintenance"):
            blockers.append(f"{dep} (maintenance)")
        elif not st.get("online", True):
            blockers.append(dep)
    return blockers

def update_latest_state(name, online, maintenance=False):
    ss = startup_status_for(name)
    with state_runtime_lock:
        latest_target_state[name] = {
            "online": bool(online), "maintenance": bool(maintenance), "updated": time.time(),
            "verified": bool(ss.get("verified", True))
        }

def flapping_status(target):
    cfg = monitoring_settings_for(target)
    window_seconds = max(60, int(cfg.get("flapping_window_seconds", 900)))
    threshold = max(2, int(cfg.get("flapping_transition_threshold", 4)))
    now = time.time()
    name = target["name"]
    with flap_lock:
        q = flap_runtime[name]
        cutoff = now - window_seconds
        while q and q[0] < cutoff:
            q.popleft()
        active = len(q) >= threshold
        previous = bool(flap_active.get(name, False))
        flap_active[name] = active
        return active, len(q), window_seconds, threshold, (active and not previous)

def record_flap_transition(target, transition):
    if transition not in ("OFFLINE", "RECOVERED"):
        return
    cfg = monitoring_settings_for(target)
    window_seconds = max(60, int(cfg.get("flapping_window_seconds", 900)))
    threshold = max(2, int(cfg.get("flapping_transition_threshold", 4)))
    now_ts = time.time()
    name = target["name"]
    with flap_lock:
        q = flap_runtime[name]
        q.append(now_ts)
        cutoff = now_ts - window_seconds
        while q and q[0] < cutoff:
            q.popleft()
        active = len(q) >= threshold
        previous = bool(flap_active.get(name, False))
        flap_active[name] = active
        count = len(q)
        entered = active and not previous
    if entered:
        with db_write_lock, closing(db_connect()) as conn:
            conn.execute(
                "INSERT INTO events(target,observed_at,category,detail) VALUES(?,?,?,?)",
                (name, now_iso(), "FLAPPING", f"{count} confirmed state changes within {window_seconds//60} minutes")
            )
            conn.commit()

def alert_suppression(target):
    maint, label = maintenance_status(target)
    if maint:
        return True, f"maintenance: {label or 'scheduled maintenance'}", []
    blockers = dependency_blockers(target)
    if blockers:
        return True, "dependency unavailable: " + ", ".join(blockers), blockers
    return False, None, []

# --- ICMP ------------------------------------------------------------------
# Works with Linux/macOS iputils/BSD ping and Windows ping.exe in any UI language
# (English, Czech, ...). A reply line is recognised by "ttl=" which every
# platform prints for genuine echo replies; Windows "Destination host
# unreachable" answers have no TTL and are therefore counted as lost.
_REPLY_TTL_RE = re.compile(r"\bttl[=:]\s*\d+", re.IGNORECASE)
_REPLY_TIME_RE = re.compile(r"[=<]\s*([0-9]+(?:[.,][0-9]+)?)\s*ms\b", re.IGNORECASE)
_PING_CREATIONFLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0) if IS_WINDOWS else 0


def _ping_command(host, count, timeout_s, interval=None):
    if IS_WINDOWS:
        # -n count, -w timeout per reply in milliseconds. No interval option exists.
        return ["ping", "-n", str(count), "-w", str(max(100, int(timeout_s * 1000))), host]
    cmd = ["ping", "-n", "-c", str(count)]
    if sys.platform == "darwin":
        cmd += ["-W", str(max(1, int(math.ceil(timeout_s * 1000))))]  # macOS: milliseconds
    else:
        cmd += ["-W", str(max(1, int(math.ceil(timeout_s))))]
    if interval is not None:
        cmd += ["-i", str(interval)]
    return cmd + [host]


def _decode_ping_output(data):
    if not data:
        return ""
    for enc in (("oem", "mbcs", "utf-8") if IS_WINDOWS else ("utf-8",)):
        try:
            return data.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return data.decode("utf-8", errors="replace")


def parse_ping_replies(output):
    """Return the list of reply round-trip times (ms) found in ping output.
    A reply without a parseable time (e.g. Windows "time<1ms" is parsed as 1.0)
    is still counted, with None as latency."""
    replies = []
    for line in (output or "").splitlines():
        if not _REPLY_TTL_RE.search(line):
            continue
        m = _REPLY_TIME_RE.search(line)
        replies.append(float(m.group(1).replace(",", ".")) if m else None)
    return replies


def _run_ping(cmd, timeout):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout,
                       check=False, creationflags=_PING_CREATIONFLAGS)
    return p.returncode, _decode_ping_output(p.stdout)


def ping_host(host):
    try:
        code, output = _run_ping(_ping_command(host, 1, PING_TIMEOUT), PING_TIMEOUT + 2.0)
    except FileNotFoundError:
        return False, None, "ping command not installed"
    except subprocess.TimeoutExpired:
        return False, None, "ping timeout"
    replies = parse_ping_replies(output)
    if replies:
        return True, replies[0], None
    short = " ".join(line.strip() for line in output.splitlines() if line.strip())[-240:]
    return False, None, short or f"ping exited {code}"


def burst_probe(host, packets=8, timeout=8):
    """Short, low-bandwidth ICMP burst. This measures path quality, not throughput."""
    packets = max(3, min(50, int(packets)))
    timeout = max(2, min(60, int(timeout)))
    started = time.perf_counter()
    # 0.2 s is the smallest interval unprivileged Linux ping accepts on every distro.
    cmd = _ping_command(host, packets, 1.0, interval=None if IS_WINDOWS else 0.2)
    try:
        _code, out = _run_ping(cmd, max(timeout, packets * 1.3 + 2))
    except FileNotFoundError:
        return {"ok": False, "error": "ping command not installed", "packets": packets}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "burst probe timeout", "packets": packets,
                "duration_ms": round((time.perf_counter() - started) * 1000, 1)}
    replies = parse_ping_replies(out)
    times = [x for x in replies if x is not None]
    loss = round((packets - min(packets, len(replies))) * 100.0 / packets, 1)
    diffs = [abs(times[i] - times[i - 1]) for i in range(1, len(times))]
    return {"ok": bool(replies), "packets": packets, "received": len(replies), "loss_percent": loss,
            "min_ms": round(min(times), 3) if times else None,
            "avg_ms": round(sum(times) / len(times), 3) if times else None,
            "max_ms": round(max(times), 3) if times else None,
            "jitter_ms": round(sum(diffs) / len(diffs), 3) if diffs else (0.0 if times else None),
            "duration_ms": round((time.perf_counter() - started) * 1000, 1), "error": None if replies else "no replies"}


def _path_health_score(target, probe):
    name=target["name"]; cfg=monitoring_settings_for(target)
    loss=float(probe.get("loss_percent") or 0); jitter=float(probe.get("jitter_ms") or 0)
    avg=probe.get("avg_ms")
    with baseline_lock:
        base=(baseline_runtime.get(name) or {}).get("mean")
    ratio=(float(avg)/float(base)) if avg is not None and base and base>0 else None
    score=100; reasons=[]
    critical_loss=float(cfg.get("path_health_loss_critical_percent",20)); watch_loss=float(cfg.get("path_health_loss_watch_percent",5))
    watch_jitter=float(cfg.get("path_health_jitter_watch_ms",5)); watch_ratio=float(cfg.get("path_health_baseline_ratio_watch",2.5))
    if loss>=critical_loss: score-=55; reasons.append(f"burst loss {loss:.1f}%")
    elif loss>=watch_loss: score-=30; reasons.append(f"burst loss {loss:.1f}%")
    elif loss>0: score-=12; reasons.append(f"burst loss {loss:.1f}%")
    if jitter>=watch_jitter*3: score-=30; reasons.append(f"jitter {jitter:.1f} ms")
    elif jitter>=watch_jitter: score-=15; reasons.append(f"jitter {jitter:.1f} ms")
    if ratio is not None and ratio>=watch_ratio*2: score-=30; reasons.append(f"latency {ratio:.1f}× baseline")
    elif ratio is not None and ratio>=watch_ratio: score-=15; reasons.append(f"latency {ratio:.1f}× baseline")
    flap, count, *_=flapping_status(target)
    if flap: score-=25; reasons.append(f"flapping ({count} transitions)")
    if loss>=100: score=min(score,10); reasons.insert(0,"no replies to burst probe")
    score=max(0,min(100,int(round(score))))
    level="NORMAL" if score>=90 else "WATCH" if score>=70 else "DEGRADING" if score>=45 else "CRITICAL"
    return score,level,reasons,ratio


def path_health_probe_target(target):
    if target_url(target): return
    cfg=monitoring_settings_for(target)
    if not bool(cfg.get("path_health_enabled",True)): return
    host=target.get("host") or target.get("ip")
    if not host: return
    probe=burst_probe(host,cfg.get("path_health_burst_packets",8),cfg.get("path_health_timeout_seconds",8))
    score,level,reasons,ratio=_path_health_score(target,probe)
    rec={**probe,"score":score,"level":level,"reasons":reasons,"baseline_ratio":round(ratio,2) if ratio is not None else None,"observed_at":now_iso()}
    with path_health_lock:
        prev=(path_health_runtime.get(target["name"]) or {}).get("level")
        path_health_runtime[target["name"]]=rec
        path_health_history[target["name"]].append(rec)
    if level in ("DEGRADING","CRITICAL") and prev not in ("DEGRADING","CRITICAL"):
        with db_write_lock,closing(db_connect()) as conn:
            conn.execute("INSERT INTO events(target,observed_at,category,detail) VALUES(?,?,?,?)",
                         (target["name"],rec["observed_at"],"PATH_DEGRADED",", ".join(reasons) or "active path quality degraded")); conn.commit()
    elif level in ("NORMAL","WATCH") and prev in ("DEGRADING","CRITICAL"):
        with db_write_lock,closing(db_connect()) as conn:
            conn.execute("INSERT INTO events(target,observed_at,category,detail) VALUES(?,?,?,?)",
                         (target["name"],rec["observed_at"],"PATH_RECOVERED","active path quality returned to normal range")); conn.commit()


def path_health_loop():
    """Stagger short probes so the monitor never creates a bandwidth spike."""
    while not stop_event.is_set():
        hosts=[t for t in TARGETS if not target_url(t) and bool(monitoring_settings_for(t).get("path_health_enabled",True))]
        if not hosts:
            stop_event.wait(60); continue
        interval=max(60,int(MONITORING.get("path_health_interval_seconds",300)))
        spacing=max(0.15,min(2.0,interval/max(1,len(hosts))))
        for t in hosts:
            if stop_event.is_set(): break
            try: path_health_probe_target(t)
            except Exception: logging.exception("Path health probe failed: %s",t.get("name"))
            stop_event.wait(spacing)
        elapsed=spacing*len(hosts)
        stop_event.wait(max(5,interval-elapsed))


def path_health_for(target_name):
    with path_health_lock:
        return dict(path_health_runtime.get(target_name) or {})


def tcp_check(host, port):
    if port is None:
        return None, None
    start = time.perf_counter()
    try:
        with socket.create_connection((host, int(port)), timeout=PING_TIMEOUT):
            return True, round((time.perf_counter() - start) * 1000, 2)
    except OSError as exc:
        return False, str(exc)


def _status_matches(status, expected):
    if expected is None:
        return 200 <= status < 400
    if isinstance(expected, (list, tuple, set)):
        return any(_status_matches(status, x) for x in expected)
    if isinstance(expected, str):
        value = expected.strip()
        if "-" in value:
            try:
                lo, hi = value.split("-", 1)
                return int(lo) <= status <= int(hi)
            except ValueError:
                pass
        try:
            return status == int(value)
        except ValueError:
            return False
    return status == int(expected)

def http_check(url, verify_ssl=True, expected_status=None, expected_body_contains=None,
               expected_body_regex=None, forbidden_body_contains=None, max_body_bytes=65536):
    """Perform a real HTTP GET with phase timing and optional response-content validation."""
    total_start = time.perf_counter()
    hard_deadline = total_start + max(0.5, float(HTTP_TIMEOUT))
    def remaining():
        left = hard_deadline - time.perf_counter()
        if left <= 0:
            raise TimeoutError(f"HTTP check exceeded {HTTP_TIMEOUT:.1f}s hard deadline")
        return max(0.05, left)

    def resolve_with_deadline(host, port):
        box, done = {}, threading.Event()
        def worker():
            try:
                box["value"] = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
            except BaseException as exc:
                box["error"] = exc
            finally:
                done.set()
        threading.Thread(target=worker, name=f"dns-{host}", daemon=True).start()
        if not done.wait(remaining()):
            raise TimeoutError(f"DNS resolution exceeded HTTP deadline for {host}")
        if "error" in box:
            raise box["error"]
        return box.get("value") or []
    timings = {"dns_ms": None, "tcp_connect_ms": None, "tls_ms": None, "server_response_ms": None,
               "tls_expires_at": None, "tls_days_left": None}
    raw_sock = None
    sock = None
    try:
        parsed = urllib.parse.urlsplit(url)
        scheme = parsed.scheme.lower()
        if scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError("URL must start with http:// or https:// and include a hostname")
        host = parsed.hostname
        port = parsed.port or (443 if scheme == "https" else 80)
        path = urllib.parse.urlunsplit(("", "", parsed.path or "/", parsed.query, ""))

        dns_start = time.perf_counter()
        addresses = resolve_with_deadline(host, port)
        timings["dns_ms"] = round((time.perf_counter() - dns_start) * 1000, 2)
        if not addresses:
            raise OSError("DNS returned no addresses")

        last_connect_error = None
        tcp_start = time.perf_counter()
        for family, socktype, proto, _canonname, sockaddr in addresses:
            candidate = None
            try:
                candidate = socket.socket(family, socktype, proto)
                candidate.settimeout(remaining())
                candidate.connect(sockaddr)
                candidate.settimeout(remaining())
                raw_sock = candidate
                break
            except OSError as exc:
                last_connect_error = exc
                if candidate is not None:
                    candidate.close()
        timings["tcp_connect_ms"] = round((time.perf_counter() - tcp_start) * 1000, 2)
        if raw_sock is None:
            raise last_connect_error or ConnectionError("TCP connection failed")

        sock = raw_sock
        if scheme == "https":
            context = ssl.create_default_context() if verify_ssl else ssl._create_unverified_context()
            tls_start = time.perf_counter()
            raw_sock.settimeout(remaining())
            sock = context.wrap_socket(raw_sock, server_hostname=host)
            sock.settimeout(remaining())
            timings["tls_ms"] = round((time.perf_counter() - tls_start) * 1000, 2)
            try:
                cert = sock.getpeercert()
                not_after = cert.get("notAfter") if cert else None
                if not_after:
                    expires_epoch = ssl.cert_time_to_seconds(not_after)
                    expires = datetime.fromtimestamp(expires_epoch, timezone.utc).astimezone()
                    timings["tls_expires_at"] = expires.isoformat(timespec="seconds")
                    timings["tls_days_left"] = round((expires_epoch - time.time()) / 86400.0, 2)
            except Exception:
                pass

        default_port = 443 if scheme == "https" else 80
        host_header = host if port == default_port else f"{host}:{port}"
        request_bytes = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host_header}\r\n"
            "User-Agent: IP-Stability-Monitor/5.0\r\n"
            "Accept: */*\r\n"
            "Accept-Encoding: identity\r\n"
            "Connection: close\r\n\r\n"
        ).encode("ascii", "strict")
        sock.settimeout(remaining())
        sock.sendall(request_bytes)
        sock.settimeout(remaining())
        response_start = time.perf_counter()
        resp = http.client.HTTPResponse(sock)
        resp.begin()
        sock.settimeout(remaining())
        timings["server_response_ms"] = round((time.perf_counter() - response_start) * 1000, 2)
        status = int(resp.status)

        content_checks = expected_body_contains is not None or expected_body_regex is not None or forbidden_body_contains is not None
        read_limit = max(1, min(1024 * 1024, int(max_body_bytes or 65536))) if content_checks else 1
        sock.settimeout(remaining())
        body = resp.read(read_limit)
        latency = round((time.perf_counter() - total_start) * 1000, 2)

        errors = []
        if not _status_matches(status, expected_status):
            errors.append(f"HTTP {status}: {resp.reason}")

        if content_checks:
            charset = "utf-8"
            try:
                charset = resp.headers.get_content_charset() or "utf-8"
            except Exception:
                pass
            text = body.decode(charset, errors="replace")
            required = expected_body_contains
            if required is not None:
                if isinstance(required, str):
                    required = [required]
                missing = [str(x) for x in required if str(x) not in text]
                if missing:
                    errors.append("expected content missing: " + ", ".join(repr(x) for x in missing[:3]))
            if expected_body_regex:
                try:
                    if re.search(str(expected_body_regex), text, flags=re.MULTILINE) is None:
                        errors.append(f"expected body regex did not match: {expected_body_regex}")
                except re.error as exc:
                    errors.append(f"invalid expected_body_regex: {exc}")
            forbidden = forbidden_body_contains
            if forbidden is not None:
                if isinstance(forbidden, str):
                    forbidden = [forbidden]
                found = [str(x) for x in forbidden if str(x) in text]
                if found:
                    errors.append("forbidden content present: " + ", ".join(repr(x) for x in found[:3]))

        ok = not errors
        return ok, latency, status, "; ".join(errors) if errors else None, timings
    except ssl.SSLCertVerificationError as exc:
        return False, round((time.perf_counter() - total_start) * 1000, 2), None, f"TLS certificate verification failed: {exc.verify_message}", timings
    except Exception as exc:
        return False, round((time.perf_counter() - total_start) * 1000, 2), None, f"{type(exc).__name__}: {exc}", timings
    finally:
        try:
            if sock is not None:
                sock.close()
            elif raw_sock is not None:
                raw_sock.close()
        except Exception:
            pass

def monitoring_settings_for(target):
    base = dict(MONITORING)
    group_overrides = base.pop("group_overrides", {}) or {}
    group = str(target.get("group", "Ungrouped")).strip() or "Ungrouped"
    if isinstance(group_overrides.get(group), dict):
        base.update(group_overrides[group])
    if isinstance(target.get("monitoring"), dict):
        base.update(target["monitoring"])
    return base


def load_monitoring_runtime():
    """Restore durable history/baselines, but require fresh evidence for current live state."""
    global startup_started_at, startup_complete
    startup_started_at = time.time()
    startup_complete = False
    with closing(db_connect()) as conn:
        rows = conn.execute(
            "SELECT target,online,stability_confirmed,observed_at,baseline_latency_ms,baseline_variance,baseline_samples FROM target_state"
        ).fetchall()

    target_names = {t["name"] for t in TARGETS}
    with stability_lock, baseline_lock, state_runtime_lock, startup_lock:
        stability_runtime.clear()
        latest_target_state.clear()
        startup_runtime.clear()
        persisted_effective_state.clear()
        for t in TARGETS:
            startup_runtime[t["name"]] = {
                "verified": False, "checks": 0, "successes": 0, "failures": 0,
                "last_raw_ok": None, "last_error": None, "verified_at": None
            }
        for r in rows:
            name = r["target"]
            if name not in target_names:
                continue
            persisted_effective_state[name] = bool(r["online"])
            # A new process/monitoring host starts with an unknown live state.
            # Persisted state is retained only as historical context for a later transition.
            stability_runtime[name] = {"state": None, "confirmed": False, "window": deque()}
            latest_target_state[name] = {"online": True, "maintenance": False, "updated": 0, "verified": False}
            if r["baseline_latency_ms"] is not None:
                baseline_runtime[name] = {
                    "mean": float(r["baseline_latency_ms"]),
                    "var": float(r["baseline_variance"] or 0),
                    "samples": int(r["baseline_samples"] or 0)
                }

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).astimezone().isoformat(timespec="seconds")
    with closing(db_connect()) as conn:
        transitions = conn.execute(
            "SELECT target,observed_at FROM events WHERE category IN ('OFFLINE','RECOVERED') AND observed_at>=? ORDER BY id",
            (cutoff,)
        ).fetchall()
    with flap_lock:
        for ev in transitions:
            try:
                flap_runtime[ev["target"]].append(datetime.fromisoformat(ev["observed_at"]).timestamp())
            except Exception:
                pass


def startup_observation(target, raw_ok, err=None):
    """Reconcile a target after process/host restart using only fresh observations."""
    global startup_complete
    cfg = monitoring_settings_for(target)
    enabled = bool(cfg.get("startup_reconciliation", True))
    name = target["name"]
    if not enabled:
        return None

    success_need = max(1, int(cfg.get("startup_success_checks", 2)))
    failure_need = max(1, int(cfg.get("startup_failure_checks", 3)))
    with startup_lock:
        st = startup_runtime.setdefault(name, {
            "verified": False, "checks": 0, "successes": 0, "failures": 0,
            "last_raw_ok": None, "last_error": None, "verified_at": None
        })
        if st["verified"]:
            return None
        st["checks"] += 1
        st["last_raw_ok"] = bool(raw_ok)
        st["last_error"] = err
        if raw_ok:
            st["successes"] += 1
            st["failures"] = 0
        else:
            st["failures"] += 1
            st["successes"] = 0

        verified = st["successes"] >= success_need or st["failures"] >= failure_need
        if verified:
            st["verified"] = True
            st["verified_at"] = now_iso()
            startup_complete = all(v.get("verified") for v in startup_runtime.values()) if startup_runtime else True
        return dict(st)


def startup_status_for(name):
    with startup_lock:
        return dict(startup_runtime.get(name, {}))


def stability_decision(target, raw_ok):
    """Debounce outages. One isolated failed check is packet loss, not an outage."""
    cfg = monitoring_settings_for(target)
    window_size = max(3, int(cfg.get("failure_window_checks", DEFAULT_FAILURE_WINDOW)))
    fail_threshold = min(window_size, max(1, int(cfg.get("failure_threshold", DEFAULT_FAILURE_THRESHOLD))))
    recovery_threshold = min(window_size, max(1, int(cfg.get("recovery_success_threshold", DEFAULT_RECOVERY_THRESHOLD))))
    name = target["name"]
    with stability_lock:
        st = stability_runtime.setdefault(name, {"state": None, "confirmed": False, "window": deque()})
        w = st["window"]
        w.append(bool(raw_ok))
        while len(w) > window_size:
            w.popleft()
        failures = sum(1 for x in w if not x)
        successes = len(w) - failures
        transition = None
        if st["state"] is None:
            cfg_start = monitoring_settings_for(target)
            startup_success = max(1, int(cfg_start.get("startup_success_checks", 2)))
            startup_failure = max(1, int(cfg_start.get("startup_failure_checks", 3)))
            if successes >= startup_success:
                st["state"] = True; st["confirmed"] = True
                old = persisted_effective_state.get(name)
                if old is False:
                    transition = "RECOVERED"
            elif failures >= startup_failure:
                st["state"] = False; st["confirmed"] = True
                old = persisted_effective_state.get(name)
                if old is True:
                    transition = "OFFLINE"
        elif st["state"]:
            if failures >= fail_threshold:
                st["state"] = False; st["confirmed"] = True; transition = "OFFLINE"
        else:
            if successes >= recovery_threshold:
                st["state"] = True; st["confirmed"] = True; transition = "RECOVERED"
        # Before enough evidence exists for a brand-new target, display the raw state as provisional.
        effective = bool(raw_ok) if st["state"] is None else bool(st["state"])
        return effective, bool(st["confirmed"]), transition, len(w), failures


def baseline_diagnostic(target, latency, raw_ok, kind):
    """Slow EWMA baseline + variance. Returns anomaly diagnostics before learning this sample."""
    cfg = monitoring_settings_for(target)
    enabled = bool(cfg.get("baseline_enabled", BASELINE_ENABLED))
    if not enabled or latency is None or not raw_ok:
        with baseline_lock:
            b = baseline_runtime.get(target["name"])
            return {"baseline_latency_ms": round(b["mean"], 2) if b else None, "baseline_variance": b["var"] if b else 0.0,
                    "baseline_samples": b["samples"] if b else 0, "anomaly_z": None, "anomaly_level": "NO DATA" if not b else "NORMAL"}
    name = target["name"]
    lat = float(latency)
    tau = max(300.0, float(cfg.get("baseline_time_constant_hours", BASELINE_TAU_SECONDS/3600.0)) * 3600.0)
    alpha = 1.0 - math.exp(-max(POLL_INTERVAL, 0.1) / tau)
    min_samples = max(5, int(cfg.get("baseline_min_samples", BASELINE_MIN_SAMPLES)))
    elevated_z = float(cfg.get("anomaly_elevated_z", 2.5)); high_z = float(cfg.get("anomaly_high_z", 4.0)); severe_z = float(cfg.get("anomaly_severe_z", 6.0))
    noise_floor = float(cfg.get("baseline_noise_floor_ms", 10.0 if kind == "http" else 1.0))
    with baseline_lock:
        b = baseline_runtime.get(name)
        if b is None:
            b = {"mean": lat, "var": 0.0, "samples": 1}; baseline_runtime[name] = b
            return {"baseline_latency_ms": round(lat,2), "baseline_variance":0.0, "baseline_samples":1, "anomaly_z":None, "anomaly_level":"LEARNING"}
        mean_before = b["mean"]; var_before = max(0.0, b["var"]); samples_before = b["samples"]
        std = max(noise_floor, math.sqrt(var_before))
        z = max(0.0, (lat - mean_before) / std) if samples_before >= min_samples else None
        if z is None: level = "LEARNING"
        elif z >= severe_z: level = "SEVERE"
        elif z >= high_z: level = "HIGH"
        elif z >= elevated_z: level = "ELEVATED"
        else: level = "NORMAL"
        # Do not let an extreme spike drag the learned baseline upward quickly.
        learn_lat = min(lat, mean_before + 4.0 * std) if samples_before >= min_samples else lat
        delta = learn_lat - b["mean"]
        b["mean"] += alpha * delta
        b["var"] = (1.0-alpha) * (b["var"] + alpha * delta * delta)
        b["samples"] += 1
        return {"baseline_latency_ms": round(b["mean"],2), "baseline_variance":b["var"], "baseline_samples":b["samples"],
                "anomaly_z": round(z,2) if z is not None else None, "anomaly_level":level}

def _minute_key(observed):
    try:
        dt = datetime.fromisoformat(observed)
    except Exception:
        dt = datetime.now(timezone.utc).astimezone()
    return dt.replace(second=0, microsecond=0).isoformat(timespec="minutes")


def record_runtime_metrics(name, observed, online, latency, check_kind):
    """Update bounded in-memory windows used by the dashboard and alerts."""
    try:
        ts = datetime.fromisoformat(observed).timestamp()
    except Exception:
        ts = time.time()
    with stats_lock:
        q = recent_checks[name]
        q.append((ts, int(bool(online)), None if latency is None else float(latency), check_kind))
        # Keep only a little over 10 minutes of raw recent checks; alerts normally use 3 minutes.
        cutoff = ts - 1200
        while q and q[0][0] < cutoff:
            q.popleft()

        key = _minute_key(observed)
        b = current_minute.get(name)
        if b is None or b["minute"] != key:
            if b is not None:
                rolling_minutes[name].append(b)
            b = {"minute": key, "checks": 0, "online": 0, "lat_sum": 0.0, "lat_count": 0,
                 "jitter_sum": 0.0, "jitter_count": 0, "last_latency": None, "kind": check_kind}
            current_minute[name] = b
        b["checks"] += 1
        b["online"] += int(bool(online))
        if latency is not None:
            lat = float(latency)
            if b["last_latency"] is not None:
                b["jitter_sum"] += abs(lat - b["last_latency"])
                b["jitter_count"] += 1
            b["last_latency"] = lat
            b["lat_sum"] += lat
            b["lat_count"] += 1


def store_result(name, endpoint, port, observed, raw_online, effective_online, ping_ok, tcp_ok, latency, err,
                 check_kind="host", http_status=None, verify_ssl=None, timings=None, transition=None,
                 stability_confirmed=True, window_checks=0, window_failures=0, baseline=None,
                 maintenance=False, maintenance_label=None):
    timings = timings or {}
    baseline = baseline or {}
    # Planned maintenance is measured and stored, but excluded from live SLA/loss windows.
    if not maintenance:
        record_runtime_metrics(name, observed, raw_online, latency, check_kind)
    with db_write_lock:
        with closing(db_connect()) as conn:
            prev = conn.execute("SELECT * FROM target_state WHERE target=?", (name,)).fetchone()
            if maintenance:
                failures = int(prev["consecutive_failures"]) if prev else 0
            else:
                failures = (int(prev["consecutive_failures"]) + 1) if (prev and not raw_online) else (1 if not raw_online else 0)
            total_checks = (int(prev["total_checks"]) if prev else 0) + (0 if maintenance else 1)
            total_failures = (int(prev["total_failures"]) if prev else 0) + (0 if (raw_online or maintenance) else 1)
            state_changes = int(prev["total_state_changes"]) if prev else 0
            changed = (transition in ("OFFLINE", "RECOVERED")) and not maintenance
            if changed:
                state_changes += 1
                if transition == "RECOVERED":
                    detail = "Target reachable again after stability confirmation"
                    if check_kind == "http" and http_status is not None:
                        detail = f"HTTP {http_status} · endpoint stable/reachable again"
                else:
                    detail = f"Confirmed outage: {window_failures}/{window_checks} recent checks failed"
                    if err:
                        detail += f" · {err}"
                conn.execute("INSERT INTO events(target, observed_at, category, detail) VALUES (?,?,?,?)",
                             (name, observed, transition, detail))

            first_observed = prev["first_observed_at"] if prev else observed
            last_online = observed if (effective_online and not maintenance) else (prev["last_online_at"] if prev else None)
            last_offline = observed if (not maintenance and not effective_online and stability_confirmed) else (prev["last_offline_at"] if prev else None)

            conn.execute("""
            INSERT INTO target_state(target,host,tcp_port,observed_at,online,ping_ok,tcp_ok,latency_ms,last_error,
              consecutive_failures,total_checks,total_failures,total_state_changes,first_observed_at,last_online_at,last_offline_at,
              check_kind,http_status,verify_ssl,dns_ms,tcp_connect_ms,tls_ms,server_response_ms,raw_ok,stability_confirmed,
              failure_window_checks,failure_window_failures,baseline_latency_ms,baseline_variance,baseline_samples,anomaly_z,anomaly_level,
              tls_expires_at,tls_days_left,maintenance_active,maintenance_label)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(target) DO UPDATE SET
              host=excluded.host,tcp_port=excluded.tcp_port,observed_at=excluded.observed_at,online=excluded.online,
              ping_ok=excluded.ping_ok,tcp_ok=excluded.tcp_ok,latency_ms=excluded.latency_ms,last_error=excluded.last_error,
              consecutive_failures=excluded.consecutive_failures,total_checks=excluded.total_checks,total_failures=excluded.total_failures,
              total_state_changes=excluded.total_state_changes,first_observed_at=excluded.first_observed_at,
              last_online_at=excluded.last_online_at,last_offline_at=excluded.last_offline_at,
              check_kind=excluded.check_kind,http_status=excluded.http_status,verify_ssl=excluded.verify_ssl,
              dns_ms=excluded.dns_ms,tcp_connect_ms=excluded.tcp_connect_ms,tls_ms=excluded.tls_ms,server_response_ms=excluded.server_response_ms,
              raw_ok=excluded.raw_ok,stability_confirmed=excluded.stability_confirmed,
              failure_window_checks=excluded.failure_window_checks,failure_window_failures=excluded.failure_window_failures,
              baseline_latency_ms=excluded.baseline_latency_ms,baseline_variance=excluded.baseline_variance,baseline_samples=excluded.baseline_samples,
              anomaly_z=excluded.anomaly_z,anomaly_level=excluded.anomaly_level,tls_expires_at=excluded.tls_expires_at,tls_days_left=excluded.tls_days_left,
              maintenance_active=excluded.maintenance_active,maintenance_label=excluded.maintenance_label
            """, (name, endpoint, port, observed, int(effective_online), int(bool(ping_ok)), None if tcp_ok is None else int(tcp_ok), latency, err,
                  failures, total_checks, total_failures, state_changes, first_observed, last_online, last_offline,
                  check_kind, http_status, None if verify_ssl is None else int(bool(verify_ssl)),
                  timings.get("dns_ms"), timings.get("tcp_connect_ms"), timings.get("tls_ms"), timings.get("server_response_ms"),
                  int(bool(raw_online)), int(bool(stability_confirmed)), int(window_checks), int(window_failures),
                  baseline.get("baseline_latency_ms"), baseline.get("baseline_variance",0.0), baseline.get("baseline_samples",0),
                  baseline.get("anomaly_z"), baseline.get("anomaly_level"), timings.get("tls_expires_at"), timings.get("tls_days_left"),
                  int(bool(maintenance)), maintenance_label))

            now_ts = time.time()
            due = now_ts - last_sample_persist.get(name, 0) >= SAMPLE_INTERVAL
            if due or changed or (not raw_online and not maintenance):
                conn.execute("""
                  INSERT INTO samples(target,observed_at,online,latency_ms,ping_ok,tcp_ok,error,check_kind,http_status,dns_ms,tcp_connect_ms,tls_ms,server_response_ms,maintenance)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (name, observed, int(raw_online), latency, int(bool(ping_ok)), None if tcp_ok is None else int(tcp_ok), err,
                      check_kind, http_status, timings.get("dns_ms"), timings.get("tcp_connect_ms"), timings.get("tls_ms"),
                      timings.get("server_response_ms"), int(bool(maintenance))))
                last_sample_persist[name] = now_ts
            conn.commit()

def parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def alert_settings_for(target):
    """Merge global alert thresholds with optional group and target overrides."""
    base = dict(EMAIL_ALERTS)
    base.pop("smtp", None)
    group_overrides = EMAIL_ALERTS.get("group_overrides", {}) or {}
    group = str(target.get("group", "Ungrouped")).strip() or "Ungrouped"
    if isinstance(group_overrides.get(group), dict):
        base.update(group_overrides[group])
    if isinstance(target.get("alerts"), dict):
        base.update(target["alerts"])
    return base


def percentile(values, q):
    if not values:
        return None
    vals = sorted(float(x) for x in values)
    if len(vals) == 1:
        return vals[0]
    pos = (len(vals)-1) * q
    lo = int(math.floor(pos)); hi = int(math.ceil(pos))
    if lo == hi:
        return vals[lo]
    return vals[lo] + (vals[hi]-vals[lo]) * (pos-lo)


def recent_window_metrics(target_name, window_seconds):
    cutoff = time.time() - window_seconds
    with stats_lock:
        rows = [r for r in recent_checks.get(target_name, ()) if r[0] >= cutoff]
    if not rows:
        return None
    checks = len(rows); online_count = sum(r[1] for r in rows)
    lat = [r[2] for r in rows if r[2] is not None]
    diffs = [abs(lat[i] - lat[i-1]) for i in range(1, len(lat))]
    return {"checks": checks, "failures": checks-online_count, "availability": round(online_count*100.0/checks,3), "packet_loss": round((checks-online_count)*100.0/checks,3),
            "avg_latency": round(sum(lat)/len(lat),2) if lat else None, "jitter": round(sum(diffs)/len(diffs),2) if diffs else None,
            "p50_latency": round(percentile(lat,.50),2) if lat else None, "p95_latency": round(percentile(lat,.95),2) if lat else None,
            "p99_latency": round(percentile(lat,.99),2) if lat else None, "kind": rows[-1][3] or "host"}


def recent_alert_metrics(target_name, window_seconds):
    return recent_window_metrics(target_name, window_seconds)

def evaluate_alert_condition(target, current_online):
    if not ALERTS_ENABLED:
        return False, None, None, None
    settings = alert_settings_for(target)
    if not bool(settings.get("enabled", True)):
        return False, None, None, settings

    window = max(30, int(settings.get("statistics_window_seconds", ALERT_DEGRADATION_SECONDS)))
    metrics = recent_alert_metrics(target["name"], window)
    if not metrics:
        return False, None, None, settings

    score = experience_score(
        metrics["kind"], bool(current_online), metrics["availability"],
        metrics["avg_latency"], metrics["jitter"], 0,
    )["score"]

    reasons = []
    if settings.get("offline", True) and not bool(current_online):
        reasons.append("target is offline")
    health_below = settings.get("health_score_below", 55)
    if health_below is not None and score is not None and score < float(health_below):
        reasons.append(f"stability score {score}/100 is below {health_below}")
    minimum_failed_checks = max(1, int(settings.get("minimum_failed_checks", 3)))
    availability_below = settings.get("availability_below", 99.0)
    if availability_below is not None and metrics.get("failures", 0) >= minimum_failed_checks and metrics["availability"] < float(availability_below):
        reasons.append(f"availability {metrics['availability']:.3f}% is below {availability_below}% ({metrics.get('failures',0)} failed checks)")
    if metrics["kind"] == "http":
        latency_limit = settings.get("http_latency_above_ms", settings.get("latency_above_ms", 1000))
        jitter_limit = settings.get("http_jitter_above_ms", settings.get("jitter_above_ms", 300))
    else:
        latency_limit = settings.get("latency_above_ms", 100)
        jitter_limit = settings.get("jitter_above_ms", 30)
    if latency_limit is not None and metrics["avg_latency"] is not None and metrics["avg_latency"] > float(latency_limit):
        reasons.append(f"average response {metrics['avg_latency']:.2f} ms exceeds {latency_limit} ms")
    if jitter_limit is not None and metrics["jitter"] is not None and metrics["jitter"] > float(jitter_limit):
        reasons.append(f"jitter {metrics['jitter']:.2f} ms exceeds {jitter_limit} ms")
    packet_loss_limit = settings.get("packet_loss_above_percent")
    if packet_loss_limit is not None and metrics.get("failures", 0) >= minimum_failed_checks and metrics.get("packet_loss") is not None and metrics["packet_loss"] > float(packet_loss_limit):
        reasons.append(f"packet loss {metrics['packet_loss']:.2f}% exceeds {packet_loss_limit}%")
    p95_limit = settings.get("http_p95_latency_above_ms" if metrics["kind"] == "http" else "p95_latency_above_ms")
    if p95_limit is not None and metrics.get("p95_latency") is not None and metrics["p95_latency"] > float(p95_limit):
        reasons.append(f"p95 response {metrics['p95_latency']:.2f} ms exceeds {p95_limit} ms")
    with baseline_lock:
        diag = dict(current_diagnostics.get(target["name"], {}))
    anomaly_levels = set(str(x).upper() for x in settings.get("alert_on_anomaly_levels", ["HIGH","SEVERE"]))
    if str(diag.get("anomaly_level", "")).upper() in anomaly_levels:
        reasons.append(f"latency anomaly {diag.get('anomaly_level')} (z={diag.get('anomaly_z')})")
    flap, flap_count, flap_window, flap_threshold, _entered = flapping_status(target)
    if bool(settings.get("alert_on_flapping", True)) and flap:
        reasons.append(f"target is flapping ({flap_count} state changes / {flap_window//60}m)")
    tls_days = diag.get("tls_days_left")
    tls_warn = settings.get("tls_expiry_warning_days", monitoring_settings_for(target).get("tls_expiry_warning_days", 30))
    if tls_days is not None and tls_warn is not None and float(tls_days) <= float(tls_warn):
        reasons.append(f"TLS certificate expires in {float(tls_days):.1f} days")
    return bool(reasons), "; ".join(reasons), {**metrics, **diag, "score": score, "window_seconds": window}, settings

def smtp_password(smtp_cfg):
    env_name = smtp_cfg.get("password_env")
    if env_name:
        return os.environ.get(str(env_name), "")
    return str(smtp_cfg.get("password", ""))


def send_alert_email(target, subject, lines, recipients_override=None):
    smtp_cfg = EMAIL_ALERTS.get("smtp", {}) or {}
    host = str(smtp_cfg.get("host", "")).strip()
    recipients = recipients_override if recipients_override is not None else smtp_cfg.get("to", [])
    if isinstance(recipients, str):
        recipients = [recipients]
    recipients = [str(x).strip() for x in recipients if str(x).strip()]
    sender = str(smtp_cfg.get("from", smtp_cfg.get("username", ""))).strip()
    if not host or not recipients or not sender:
        logging.error("Email alert not sent for %s: SMTP host/from/to is incomplete", target["name"])
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.set_content("\n".join(lines))

    port = int(smtp_cfg.get("port", 587))
    timeout = float(smtp_cfg.get("timeout_seconds", 10))
    username = str(smtp_cfg.get("username", "")).strip()
    password = smtp_password(smtp_cfg)
    use_ssl = bool(smtp_cfg.get("ssl", False))
    use_starttls = bool(smtp_cfg.get("starttls", not use_ssl))

    try:
        server_cls = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
        with server_cls(host, port, timeout=timeout) as smtp:
            if not use_ssl and use_starttls:
                smtp.starttls(context=ssl.create_default_context())
            if username:
                smtp.login(username, password)
            smtp.send_message(msg)
        logging.info("Email alert sent for %s: %s", target["name"], subject)
        return True
    except Exception:
        logging.exception("Failed to send email alert for %s", target["name"])
        return False


def format_alert_lines(target, metrics, reason, duration_seconds, recovery=False):
    endpoint = target_display(target)
    group = str(target.get("group", "Ungrouped")).strip() or "Ungrouped"
    status = "RECOVERED" if recovery else "DEGRADED"
    lines = [
        f"{status} — {target['name']}",
        "",
        f"Group: {group}",
        f"Endpoint: {endpoint}",
        f"Duration: {int(duration_seconds)//60}m {int(duration_seconds)%60:02d}s",
    ]
    if metrics:
        if metrics.get("score") is not None:
            lines.append(f"Stability score: {metrics['score']}/100")
        lines.append(f"Availability ({metrics.get('window_seconds', 0)}s window): {metrics['availability']:.3f}%")
        if metrics.get("avg_latency") is not None:
            lines.append(f"Average response: {metrics['avg_latency']:.2f} ms")
        if metrics.get("jitter") is not None:
            lines.append(f"Jitter: {metrics['jitter']:.2f} ms")
        if metrics.get("packet_loss") is not None:
            lines.append(f"Packet loss: {metrics['packet_loss']:.3f}%")
        if metrics.get("p95_latency") is not None:
            lines.append(f"P95 response: {metrics['p95_latency']:.2f} ms")
        if metrics.get("anomaly_level") not in (None, "NORMAL", "LEARNING", "NO DATA"):
            lines.append(f"Latency anomaly: {metrics.get('anomaly_level')} (z={metrics.get('anomaly_z')})")
        if metrics.get("tls_days_left") is not None:
            lines.append(f"TLS certificate days remaining: {metrics['tls_days_left']:.1f}")
    if reason:
        lines.extend(["", f"Reason: {reason}"])
    lines.extend(["", f"Observed: {now_iso()}"])
    return lines


def _load_alert_runtime_once():
    if not ALERTS_ENABLED:
        return
    with closing(db_connect()) as conn:
        rows = conn.execute("SELECT * FROM alert_state").fetchall()
    with alert_lock:
        for r in rows:
            alert_runtime[r["target"]] = dict(r)


def _persist_alert_state(name, st):
    with db_write_lock:
        with closing(db_connect()) as conn:
            conn.execute("""
              INSERT INTO alert_state(target,condition_active,condition_since,alert_sent,alerted_at,recovering_since,
                last_reminder_at,last_reason,last_score,last_metrics,escalated_at)
              VALUES(?,?,?,?,?,?,?,?,?,?,?)
              ON CONFLICT(target) DO UPDATE SET condition_active=excluded.condition_active,
                condition_since=excluded.condition_since,alert_sent=excluded.alert_sent,alerted_at=excluded.alerted_at,
                recovering_since=excluded.recovering_since,last_reminder_at=excluded.last_reminder_at,
                last_reason=excluded.last_reason,last_score=excluded.last_score,last_metrics=excluded.last_metrics,
                escalated_at=excluded.escalated_at
            """, (name, int(bool(st.get("condition_active"))), st.get("condition_since"), int(bool(st.get("alert_sent"))),
                  st.get("alerted_at"), st.get("recovering_since"), st.get("last_reminder_at"), st.get("last_reason"),
                  st.get("last_score"), st.get("last_metrics"), st.get("escalated_at")))
            conn.commit()


def process_alert_state(target, current_online):
    if not ALERTS_ENABLED:
        return

    suppressed, suppression_reason, blockers = alert_suppression(target)
    name = target["name"]
    if suppressed:
        # Suppression never creates a false recovery. Pending unsent timers are cleared;
        # an already-sent incident is simply frozen until dependencies/maintenance clear.
        with alert_lock:
            st = alert_runtime.setdefault(name, {"condition_active": 0, "condition_since": None, "alert_sent": 0,
                "alerted_at": None, "recovering_since": None, "last_reminder_at": None, "last_reason": None,
                "last_score": None, "last_metrics": None, "escalated_at": None})
            dirty = False
            if not st.get("alert_sent") and (st.get("condition_since") or st.get("condition_active") or st.get("recovering_since")):
                st.update({"condition_active": 0, "condition_since": None, "recovering_since": None, "last_reason": suppression_reason})
                dirty = True
            if dirty:
                _persist_alert_state(name, st)
        return

    bad, reason, metrics, settings = evaluate_alert_condition(target, current_online)
    if settings is None or not bool(settings.get("enabled", True)):
        return
    now = datetime.now(timezone.utc).astimezone()
    degradation_seconds = max(1, int(settings.get("degradation_seconds", ALERT_DEGRADATION_SECONDS)))
    recovery_seconds = max(1, int(settings.get("recovery_seconds", ALERT_RECOVERY_SECONDS)))
    reminder_seconds = max(0, int(settings.get("reminder_seconds", ALERT_REMINDER_SECONDS)))
    escalation_seconds = max(0, int(settings.get("escalation_seconds", 0)))
    send_recovery = bool(settings.get("send_recovery", True))

    with alert_lock:
        st = alert_runtime.setdefault(name, {"condition_active": 0, "condition_since": None, "alert_sent": 0,
            "alerted_at": None, "recovering_since": None, "last_reminder_at": None, "last_reason": None,
            "last_score": None, "last_metrics": None, "escalated_at": None})
        dirty = False
        condition_since = parse_iso(st.get("condition_since"))
        alerted_at = parse_iso(st.get("alerted_at"))
        recovering_since = parse_iso(st.get("recovering_since"))
        last_reminder_at = parse_iso(st.get("last_reminder_at"))
        escalated_at = parse_iso(st.get("escalated_at"))
        alert_sent = bool(st.get("alert_sent"))

        if bad:
            if condition_since is None:
                condition_since = now
                st["condition_since"] = condition_since.isoformat(timespec="seconds")
                dirty = True
            if st.get("recovering_since") is not None:
                st["recovering_since"] = None
                dirty = True
            st["condition_active"] = 1
            bad_duration = max(0, (now - condition_since).total_seconds())
            should_alert = (not alert_sent) and bad_duration >= degradation_seconds
            should_remind = (alert_sent and reminder_seconds > 0 and alerted_at is not None and
                             (now - (last_reminder_at or alerted_at)).total_seconds() >= reminder_seconds)
            should_escalate = alert_sent and escalation_seconds > 0 and escalated_at is None and bad_duration >= escalation_seconds

            if should_alert or should_remind:
                prefix = "REMINDER" if should_remind else "DEGRADED"
                subject = f"[{prefix}] {name} stability alert"
                if send_alert_email(target, subject, format_alert_lines(target, metrics, reason, bad_duration)):
                    category = "ALERT_REMINDER" if should_remind else "ALERT"
                    with db_write_lock, closing(db_connect()) as conn:
                        conn.execute("INSERT INTO events(target,observed_at,category,detail) VALUES(?,?,?,?)",
                                     (name, now_iso(), category, reason))
                        conn.commit()
                    if should_alert:
                        st["alert_sent"] = 1
                        st["alerted_at"] = now.isoformat(timespec="seconds")
                        alert_sent = True
                    if should_remind:
                        st["last_reminder_at"] = now.isoformat(timespec="seconds")
                    dirty = True

            # Recompute after an alert may have just been sent.
            if bool(st.get("alert_sent")) and escalation_seconds > 0 and not st.get("escalated_at") and bad_duration >= escalation_seconds:
                escalation_to = settings.get("escalation_to") or (EMAIL_ALERTS.get("smtp", {}) or {}).get("escalation_to")
                subject = f"[ESCALATED] {name} stability alert"
                if send_alert_email(target, subject, format_alert_lines(target, metrics, reason, bad_duration), escalation_to):
                    st["escalated_at"] = now.isoformat(timespec="seconds")
                    with db_write_lock, closing(db_connect()) as conn:
                        conn.execute("INSERT INTO events(target,observed_at,category,detail) VALUES(?,?,?,?)",
                                     (name, now_iso(), "ALERT_ESCALATED", reason))
                        conn.commit()
                    dirty = True

            if st.get("last_reason") != reason:
                st["last_reason"] = reason; dirty = True
            st["last_score"] = metrics.get("score") if metrics else None
            st["last_metrics"] = json.dumps(metrics or {})
            if dirty:
                _persist_alert_state(name, st)
            return

        if alert_sent:
            if recovering_since is None:
                recovering_since = now
                st["recovering_since"] = recovering_since.isoformat(timespec="seconds")
                st["condition_active"] = 0
                dirty = True
            healthy_duration = max(0, (now - recovering_since).total_seconds())
            if healthy_duration >= recovery_seconds:
                incident_start = condition_since or alerted_at or now
                incident_duration = max(0, (now - incident_start).total_seconds())
                if send_recovery:
                    subject = f"[RECOVERED] {name} stability restored"
                    if send_alert_email(target, subject, format_alert_lines(target, metrics, st.get("last_reason"), incident_duration, recovery=True)):
                        with db_write_lock, closing(db_connect()) as conn:
                            conn.execute("INSERT INTO events(target,observed_at,category,detail) VALUES(?,?,?,?)",
                                         (name, now_iso(), "ALERT_RECOVERED", f"Recovered after {int(incident_duration)} seconds"))
                            conn.commit()
                st.update({"condition_active": 0, "condition_since": None, "alert_sent": 0, "alerted_at": None,
                           "recovering_since": None, "last_reminder_at": None, "last_reason": None, "escalated_at": None})
                dirty = True
        else:
            if st.get("condition_since") or st.get("recovering_since") or st.get("condition_active"):
                st.update({"condition_active": 0, "condition_since": None, "recovering_since": None, "last_reason": None})
                dirty = True
        st["last_score"] = metrics.get("score") if metrics else None
        st["last_metrics"] = json.dumps(metrics or {})
        if dirty:
            _persist_alert_state(name, st)

def check_target(target):
    name = target["name"]
    observed = now_iso()
    url = target_url(target)
    maintenance, maintenance_label = maintenance_status(target)

    if url:
        verify_ssl = bool(target.get("verify_ssl", True))
        expected_status = target.get("expected_status")
        raw_ok, latency, http_status, err, timings = http_check(
            url,
            verify_ssl=verify_ssl,
            expected_status=expected_status,
            expected_body_contains=target.get("expected_body_contains"),
            expected_body_regex=target.get("expected_body_regex"),
            forbidden_body_contains=target.get("forbidden_body_contains"),
            max_body_bytes=target.get("max_body_bytes", 65536),
        )
        startup_observation(target, raw_ok, err)
        if maintenance:
            effective, confirmed, transition, wchecks, wfails = stability_snapshot(target, raw_ok)
        else:
            effective, confirmed, transition, wchecks, wfails = stability_decision(target, raw_ok)
        baseline = baseline_diagnostic(target, latency, raw_ok, "http") if not maintenance else baseline_diagnostic(target, None, False, "http")
        with baseline_lock:
            current_diagnostics[name] = {**baseline, "tls_expires_at": timings.get("tls_expires_at"), "tls_days_left": timings.get("tls_days_left")}
        store_result(name, url, None, observed, raw_ok, effective, False, None, latency, err,
                     check_kind="http", http_status=http_status, verify_ssl=verify_ssl, timings=timings,
                     transition=transition, stability_confirmed=confirmed, window_checks=wchecks, window_failures=wfails,
                     baseline=baseline, maintenance=maintenance, maintenance_label=maintenance_label)
        update_latest_state(name, effective, maintenance)
        if transition:
            record_flap_transition(target, transition)
        ss = startup_status_for(name)
        grace = max(0, int(monitoring_settings_for(target).get("startup_alert_grace_seconds", 30)))
        if ss.get("verified") and (time.time() - startup_started_at) >= grace:
            process_alert_state(target, effective)
        return

    host = target["host"]
    port = target.get("tcp_port")
    ping_ok, latency, ping_error = ping_host(host)
    tcp_ok, tcp_info = tcp_check(host, port)
    raw_ok = bool(ping_ok and (tcp_ok is not False))
    err = None
    if not ping_ok:
        err = ping_error or "ICMP unreachable"
    elif tcp_ok is False:
        err = f"TCP {port}: {tcp_info}"
    startup_observation(target, raw_ok, err)
    if maintenance:
        effective, confirmed, transition, wchecks, wfails = stability_snapshot(target, raw_ok)
    else:
        effective, confirmed, transition, wchecks, wfails = stability_decision(target, raw_ok)
    baseline = baseline_diagnostic(target, latency, raw_ok, "host") if not maintenance else baseline_diagnostic(target, None, False, "host")
    with baseline_lock:
        current_diagnostics[name] = dict(baseline)
    store_result(name, host, port, observed, raw_ok, effective, ping_ok, tcp_ok, latency, err, check_kind="host",
                 transition=transition, stability_confirmed=confirmed, window_checks=wchecks, window_failures=wfails,
                 baseline=baseline, maintenance=maintenance, maintenance_label=maintenance_label)
    update_latest_state(name, effective, maintenance)
    if transition:
        record_flap_transition(target, transition)
    ss = startup_status_for(name)
    grace = max(0, int(monitoring_settings_for(target).get("startup_alert_grace_seconds", 30)))
    if ss.get("verified") and (time.time() - startup_started_at) >= grace:
        process_alert_state(target, effective)

def cleanup_history():
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=RETENTION_DAYS)).astimezone().isoformat(timespec="seconds")
    event_cutoff = (now - timedelta(days=EVENT_RETENTION_DAYS)).astimezone().isoformat(timespec="seconds")
    try:
        with db_write_lock:
            with closing(db_connect()) as conn:
                conn.execute("DELETE FROM samples WHERE observed_at < ?", (cutoff,))
                conn.execute("DELETE FROM events WHERE observed_at < ?", (event_cutoff,))
                conn.commit()
                conn.execute("PRAGMA optimize")
    except Exception:
        logging.exception("History cleanup failed")


collector_heartbeat = {"last_sweep_at": None, "last_sweep_seconds": None, "sweeps": 0}


inflight_lock = threading.Lock()
inflight_checks = set()


def _safe_check_target(target):
    name = target.get("name", "?")
    try:
        check_target(target)
    except Exception:
        logging.exception("Target check failed unexpectedly: %s", name)
    finally:
        with inflight_lock:
            inflight_checks.discard(name)


def _submit_check(pool, target):
    """Never run two checks of the same target concurrently (e.g. a slow SMTP send)."""
    with inflight_lock:
        if target["name"] in inflight_checks:
            return None
        inflight_checks.add(target["name"])
    return pool.submit(_safe_check_target, target)

def collector_loop():
    workers = max(4, min(48, len(TARGETS) or 1))
    last_cleanup = 0
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="check") as pool:
        while not stop_event.is_set():
            started = time.monotonic()
            with startup_lock:
                order = sorted(TARGETS, key=lambda t: (startup_runtime.get(t["name"], {}).get("verified", False), int(t.get("index", 999999))))
            futures = [f for f in (_submit_check(pool, t) for t in order) if f is not None]
            # Every target has bounded network timeouts; one unexpected failure is isolated.
            if futures:
                futures_wait(futures, timeout=max(2.0, HTTP_TIMEOUT + PING_TIMEOUT + 2.0))
            collector_heartbeat["last_sweep_at"] = time.time()
            collector_heartbeat["last_sweep_seconds"] = round(time.monotonic() - started, 3)
            collector_heartbeat["sweeps"] += 1
            if time.time() - last_cleanup > 3600:
                cleanup_history()
                last_cleanup = time.time()
            wait = max(0.05, POLL_INTERVAL - (time.monotonic() - started))
            stop_event.wait(wait)


def score_curve(value, points):
    """Piecewise-linear score curve. points are (value, score), ascending by value."""
    if value is None:
        return None
    value = float(value)
    if value <= points[0][0]:
        return float(points[0][1])
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if value <= x1:
            if x1 == x0:
                return float(y1)
            f = (value - x0) / (x1 - x0)
            return float(y0 + f * (y1 - y0))
    return float(points[-1][1])


def experience_score(kind, online, uptime, avg_latency, jitter, consecutive_failures=0):
    """
    Heuristic 0..100 stability / user-experience indicator.
    This is deliberately interpretable rather than an ML prediction.
    """
    if uptime is None:
        return {"score": None, "grade": "NO DATA", "level": "unknown", "summary": "Not enough history yet"}

    # Availability is intentionally dominant. Small repeated losses are very noticeable
    # for interactive applications, voice, roaming and control traffic.
    availability_score = score_curve(100.0 - float(uptime), [
        (0.0, 100), (0.1, 96), (0.5, 82), (1.0, 68), (3.0, 38), (5.0, 18), (10.0, 0)
    ])

    if kind == "http":
        latency_score = score_curve(avg_latency, [
            (100, 100), (250, 92), (500, 78), (1000, 55), (2000, 25), (4000, 0)
        ])
        jitter_score = score_curve(jitter, [
            (20, 100), (50, 92), (150, 75), (300, 50), (750, 20), (1500, 0)
        ])
    else:
        latency_score = score_curve(avg_latency, [
            (5, 100), (10, 96), (20, 88), (50, 70), (100, 45), (250, 12), (500, 0)
        ])
        jitter_score = score_curve(jitter, [
            (1, 100), (3, 96), (5, 90), (15, 70), (30, 45), (80, 10), (150, 0)
        ])

    # Missing latency should not make an otherwise reachable endpoint look broken.
    latency_score = 80.0 if latency_score is None else latency_score
    jitter_score = 80.0 if jitter_score is None else jitter_score
    score = availability_score * 0.55 + latency_score * 0.30 + jitter_score * 0.15

    # Current state overrides historical comfort: a target that is down now should look bad now.
    if not bool(online):
        score = min(score, 18.0)
    elif int(consecutive_failures or 0) >= 2:
        score = min(score, max(35.0, 94.0 - int(consecutive_failures) * 8.0))

    score = int(round(max(0.0, min(100.0, score))))
    if score >= 90:
        grade, level = "EXCELLENT", "excellent"
    elif score >= 75:
        grade, level = "GOOD", "good"
    elif score >= 55:
        grade, level = "FAIR", "fair"
    elif score >= 35:
        grade, level = "POOR", "poor"
    else:
        grade, level = "CRITICAL", "critical"

    reasons = []
    if not bool(online):
        reasons.append("currently offline")
    if uptime < 99.9:
        reasons.append(f"{100.0-uptime:.3f}% failed checks")
    if avg_latency is not None:
        if (kind == "http" and avg_latency > 500) or (kind != "http" and avg_latency > 20):
            reasons.append(f"{avg_latency:.1f} ms average response")
    if jitter is not None:
        if (kind == "http" and jitter > 150) or (kind != "http" and jitter > 5):
            reasons.append(f"{jitter:.1f} ms jitter")
    summary = ", ".join(reasons[:2]) if reasons else "Stable response and availability"
    return {"score": score, "grade": grade, "level": level, "summary": summary}


def bootstrap_runtime_metrics():
    """Load compact 1-minute 24h summaries once at startup from existing history."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).astimezone().isoformat(timespec="seconds")
    with closing(db_connect()) as conn:
        rows = conn.execute("""
          SELECT target, substr(observed_at,1,16) AS minute, COUNT(*) AS checks, SUM(online) AS online,
                 AVG(latency_ms) AS avg_latency, COUNT(latency_ms) AS latency_count, check_kind
          FROM samples WHERE observed_at>=?
          GROUP BY target, substr(observed_at,1,16)
          ORDER BY minute
        """, (cutoff,)).fetchall()
    with stats_lock:
        for r in rows:
            avg = r["avg_latency"]
            rolling_minutes[r["target"]].append({
                "minute": r["minute"], "checks": int(r["checks"] or 0), "online": int(r["online"] or 0),
                "lat_sum": float(avg or 0) * int(r["latency_count"] or 0), "lat_count": int(r["latency_count"] or 0),
                "jitter_sum": 0.0, "jitter_count": 0, "last_latency": avg, "kind": r["check_kind"] or "host"
            })


def metrics_for_cached(target):
    cutoff = datetime.now(timezone.utc).astimezone() - timedelta(hours=24)
    with stats_lock:
        buckets = list(rolling_minutes.get(target, ()))
        if target in current_minute:
            buckets.append(dict(current_minute[target]))
    valid=[]
    for b in buckets:
        try:
            dt=datetime.fromisoformat(b["minute"])
        except Exception:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=cutoff.tzinfo)
        if dt >= cutoff:
            valid.append(b)
    checks=sum(b["checks"] for b in valid)
    if not checks:
        return {"checks_24h":0,"uptime_24h":None,"loss_24h":None,"avg_latency_24h":None,"jitter_24h":None}
    online=sum(b["online"] for b in valid)
    lat_sum=sum(b["lat_sum"] for b in valid); lat_count=sum(b["lat_count"] for b in valid)
    jitter_sum=sum(b["jitter_sum"] for b in valid); jitter_count=sum(b["jitter_count"] for b in valid)
    uptime=online*100.0/checks
    return {"checks_24h":checks,"uptime_24h":round(uptime,3),"loss_24h":round(100.0-uptime,3),
            "avg_latency_24h":round(lat_sum/lat_count,2) if lat_count else None,
            "jitter_24h":round(jitter_sum/jitter_count,2) if jitter_count else None}


CONFIG_EDIT_SCHEMA = {
    "poll_interval_seconds": {"type": "float", "min": 0.2, "max": 3600},
    "sample_interval_seconds": {"type": "float", "min": 0.2, "max": 86400},
    "ping_timeout_seconds": {"type": "float", "min": 0.1, "max": 60},
    "http_timeout_seconds": {"type": "float", "min": 0.2, "max": 120},
    "history_retention_days": {"type": "int", "min": 1, "max": 3650},
    "event_retention_days": {"type": "int", "min": 1, "max": 36500},
    "monitoring.startup_success_checks": {"type": "int", "min": 1, "max": 100},
    "monitoring.startup_failure_checks": {"type": "int", "min": 1, "max": 100},
    "monitoring.startup_alert_grace_seconds": {"type": "int", "min": 0, "max": 86400},
    "monitoring.failure_window_checks": {"type": "int", "min": 3, "max": 100},
    "monitoring.failure_threshold": {"type": "int", "min": 1, "max": 100},
    "monitoring.recovery_success_threshold": {"type": "int", "min": 1, "max": 100},
    "monitoring.baseline_enabled": {"type": "bool"},
    "monitoring.baseline_time_constant_hours": {"type": "float", "min": 0.1, "max": 720},
    "monitoring.baseline_min_samples": {"type": "int", "min": 5, "max": 100000},
    "monitoring.tls_expiry_warning_days": {"type": "float", "min": 0, "max": 3650},
    "monitoring.flapping_window_seconds": {"type": "int", "min": 60, "max": 86400},
    "monitoring.flapping_transition_threshold": {"type": "int", "min": 2, "max": 100},
    "monitoring.path_health_enabled": {"type": "bool"},
    "monitoring.path_health_interval_seconds": {"type": "int", "min": 60, "max": 86400},
    "monitoring.path_health_burst_packets": {"type": "int", "min": 3, "max": 50},
    "monitoring.path_health_timeout_seconds": {"type": "int", "min": 2, "max": 60},
    "monitoring.path_health_loss_watch_percent": {"type": "float", "min": 0, "max": 100},
    "monitoring.path_health_loss_critical_percent": {"type": "float", "min": 0, "max": 100},
    "monitoring.path_health_jitter_watch_ms": {"type": "float", "min": 0, "max": 1000},
    "monitoring.path_health_baseline_ratio_watch": {"type": "float", "min": 1, "max": 20},
    "email_alerts.enabled": {"type": "bool"},
    "email_alerts.degradation_seconds": {"type": "int", "min": 1, "max": 86400},
    "email_alerts.recovery_seconds": {"type": "int", "min": 1, "max": 86400},
    "email_alerts.reminder_seconds": {"type": "int", "min": 0, "max": 604800},
    "email_alerts.escalation_seconds": {"type": "int", "min": 0, "max": 604800},
    "email_alerts.alert_on_flapping": {"type": "bool"}
}

def _get_path(obj, path, default=None):
    cur = obj
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur

def _set_path(obj, path, value):
    parts = path.split(".")
    cur = obj
    for part in parts[:-1]:
        if not isinstance(cur.get(part), dict):
            cur[part] = {}
        cur = cur[part]
    cur[parts[-1]] = value

def _coerce_setting(spec, value):
    typ = spec["type"]
    if typ == "bool":
        if isinstance(value, bool):
            return value
        if str(value).lower() in ("true", "1", "yes", "on"):
            return True
        if str(value).lower() in ("false", "0", "no", "off"):
            return False
        raise ValueError("must be true or false")
    value = int(value) if typ == "int" else float(value)
    if "min" in spec and value < spec["min"]:
        raise ValueError(f"must be >= {spec['min']}")
    if "max" in spec and value > spec["max"]:
        raise ValueError(f"must be <= {spec['max']}")
    return value

def _public_config_settings():
    return {key: _get_path(CONFIG, key) for key in CONFIG_EDIT_SCHEMA}


# --- Optional dashboard authentication -------------------------------------
# "auth": {"username": "admin", "password_env": "IPMON_WEB_PASSWORD"}  (or "password")
# When configured, every page and API call requires HTTP Basic credentials,
# except /healthz which stays open for external uptime checks.
# "auth": {"read_only_without_login": true} lets anyone view while still
# protecting settings, restart, reset and target editing.
AUTH_OPEN_PATHS = {"/healthz"}


def _auth_settings():
    cfg = CONFIG.get("auth") or {}
    if not isinstance(cfg, dict) or cfg.get("enabled") is False:
        return None
    user = str(cfg.get("username", "") or "").strip()
    password = os.environ.get(str(cfg["password_env"]), "") if cfg.get("password_env") else str(cfg.get("password", "") or "")
    if not user or not password:
        return None
    return user, password, bool(cfg.get("read_only_without_login", False))


def _credentials_ok(expected_user, expected_password):
    header = request.headers.get("Authorization", "")
    if not header.lower().startswith("basic "):
        return False
    try:
        user, _, password = base64.b64decode(header[6:].strip()).decode("utf-8").partition(":")
    except Exception:
        return False
    return hmac.compare_digest(user.encode(), expected_user.encode()) and \
        hmac.compare_digest(password.encode(), expected_password.encode())


@app.before_request
def _require_auth():
    auth = _auth_settings()
    if auth is None or request.path in AUTH_OPEN_PATHS:
        return None
    user, password, read_only_open = auth
    if read_only_open and request.method in ("GET", "HEAD", "OPTIONS"):
        return None
    if _credentials_ok(user, password):
        return None
    return Response("Authentication required\n", 401, {"WWW-Authenticate": 'Basic realm="IP Stability Monitor", charset="UTF-8"'})


@app.after_request
def _security_headers(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    resp.headers.setdefault("Referrer-Policy", "same-origin")
    return resp

@app.get("/api/config")
def api_config_get():
    with config_lock:
        return jsonify({"settings": _public_config_settings(),
                        "defaults": {key: _get_path(CONFIG_DEFAULTS, key) for key in CONFIG_EDIT_SCHEMA},
                        "language": str((CONFIG.get("ui") or {}).get("language", "en")).lower(),
                        "auto_backfill": True})

@app.post("/api/config")
def api_config_update():
    body = request.get_json(silent=True) or {}
    incoming = body.get("settings")
    if not isinstance(incoming, dict):
        return jsonify({"ok": False, "error": "settings must be an object"}), 400
    errors, parsed = {}, {}
    for key, value in incoming.items():
        spec = CONFIG_EDIT_SCHEMA.get(key)
        if not spec:
            errors[key] = "setting is not editable from dashboard"
            continue
        try:
            parsed[key] = _coerce_setting(spec, value)
        except Exception as exc:
            errors[key] = str(exc)
    if errors:
        return jsonify({"ok": False, "errors": errors}), 400
    merged = dict(_public_config_settings()); merged.update(parsed)
    if int(merged["monitoring.failure_threshold"]) > int(merged["monitoring.failure_window_checks"]):
        return jsonify({"ok": False, "error": "failure_threshold cannot exceed failure_window_checks"}), 400
    if int(merged["monitoring.recovery_success_threshold"]) > int(merged["monitoring.failure_window_checks"]):
        return jsonify({"ok": False, "error": "recovery_success_threshold cannot exceed failure_window_checks"}), 400
    with config_lock:
        for key, value in parsed.items():
            _set_path(CONFIG, key, value)
        _write_config_atomic(CONFIG)
        apply_runtime_config()
    return jsonify({"ok": True, "settings": _public_config_settings(), "restart_required": False})

@app.post("/api/config/language")
def api_config_language():
    body = request.get_json(silent=True) or {}
    lang = str(body.get("language", "")).lower()
    if lang not in ("en", "cs"):
        return jsonify({"ok": False, "error": "language must be en or cs"}), 400
    with config_lock:
        CONFIG.setdefault("ui", {})["language"] = lang
        _write_config_atomic(CONFIG)
    return jsonify({"ok": True, "language": lang})


def _configured_groups():
    groups = []
    seen = set()
    raw_groups = CONFIG.get("groups", []) or []
    for item in raw_groups:
        name = str(item.get("name", "") if isinstance(item, dict) else item).strip()
        if name and name not in seen:
            groups.append(name); seen.add(name)
    for target in CONFIG.get("targets", []) or []:
        name = str(target.get("group", "") or "").strip()
        if name and name not in seen:
            groups.append(name); seen.add(name)
    return groups

def _validate_target_list(targets):
    if not isinstance(targets, list):
        raise ValueError("targets must be an array")
    names = set()
    for i, target in enumerate(targets, start=1):
        if not isinstance(target, dict):
            raise ValueError(f"Target #{i} must be an object")
        name = str(target.get("name", "")).strip()
        if not name:
            raise ValueError(f"Target #{i} is missing name")
        if name in names:
            raise ValueError(f"Duplicate target name: {name}")
        names.add(name)
        url = target_url(target)
        host = str(target.get("host", "") or "").strip()
        if not url and not host:
            raise ValueError(f"Target '{name}' needs host or url")
        if url:
            parsed = urllib.parse.urlsplit(url)
            if parsed.scheme.lower() not in ("http", "https") or not parsed.hostname:
                raise ValueError(f"Target '{name}' has an invalid HTTP/HTTPS URL")
        port = target.get("tcp_port")
        if port not in (None, ""):
            try:
                port = int(port)
            except Exception:
                raise ValueError(f"Target '{name}' has an invalid TCP port")
            if not 1 <= port <= 65535:
                raise ValueError(f"Target '{name}' TCP port must be 1-65535")
    graph = {}
    for target in targets:
        deps = target.get("depends_on", [])
        if isinstance(deps, str): deps = [deps]
        deps = [str(x).strip() for x in deps if str(x).strip()]
        for dep in deps:
            if dep not in names:
                raise ValueError(f"Target '{target['name']}' depends on unknown target '{dep}'")
            if dep == target['name']:
                raise ValueError(f"Target '{target['name']}' cannot depend on itself")
        graph[target['name']] = deps
    visiting, done = set(), set()
    def visit(node):
        if node in visiting: raise ValueError(f"Dependency cycle detected at '{node}'")
        if node in done: return
        visiting.add(node)
        for dep in graph.get(node, []): visit(dep)
        visiting.remove(node); done.add(node)
    for node in graph: visit(node)

@app.get("/api/targets-config")
def api_targets_get():
    with config_lock:
        targets = json.loads(json.dumps(CONFIG.get("targets", []) or []))
        groups = _configured_groups()
    return jsonify({"targets": targets, "groups": groups, "restart_required": True})

@app.post("/api/targets-config")
def api_targets_save():
    body = request.get_json(silent=True) or {}
    targets = body.get("targets")
    groups = body.get("groups", [])
    if not isinstance(groups, list):
        return jsonify({"ok": False, "error": "groups must be an array"}), 400
    clean_groups=[]; seen=set()
    for item in groups:
        name = str(item.get("name", "") if isinstance(item, dict) else item).strip()
        if not name or name in seen: continue
        clean_groups.append(name); seen.add(name)
    try:
        _validate_target_list(targets)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    # Normalize common editable fields without touching unknown advanced fields.
    normalized=[]
    for target in targets:
        t=dict(target)
        t["name"] = str(t.get("name", "")).strip()
        group = str(t.get("group", "") or "").strip()
        if group: t["group"] = group
        else: t.pop("group", None)
        if t.get("tcp_port") in ("", None): t.pop("tcp_port", None)
        elif "tcp_port" in t: t["tcp_port"] = int(t["tcp_port"])
        normalized.append(t)
    with config_lock:
        CONFIG["groups"] = clean_groups
        CONFIG["targets"] = normalized
        _write_config_atomic(CONFIG)
    return jsonify({"ok": True, "target_count": len(normalized), "groups": clean_groups, "restart_required": True})

RESTART_EXIT_CODE = 3  # start_monitor.bat / supervisors restart the process on this code
restart_lock = threading.Lock()
restart_pending = False

def _restart_process_after_delay(delay=0.8):
    """Replace this Python process with a fresh copy of itself."""
    time.sleep(delay)
    try:
        stop_event.set()
        os.environ.pop("WERKZEUG_SERVER_FD", None)
        if os.environ.get("INVOCATION_ID") or os.environ.get("IPMON_SUPERVISED"):
            # Running under systemd (or another supervisor with Restart=always):
            # exit cleanly and let the supervisor start a fresh process.
            logging.info("Restart requested; exiting with code %s for supervisor restart", RESTART_EXIT_CODE)
            os._exit(RESTART_EXIT_CODE)
        if IS_WINDOWS:
            # os.execv on Windows spawns a detached child and the parent exits, which
            # breaks console windows and the listening socket hand-off. Start a new
            # process explicitly, then terminate this one.
            subprocess.Popen([sys.executable] + sys.argv, cwd=os.getcwd(), close_fds=True)
            os._exit(0)
        # Werkzeug marks its listening socket inheritable (WERKZEUG_SERVER_FD), so it
        # would survive execv and block the new process from binding the port.
        os.environ.pop("WERKZEUG_SERVER_FD", None)
        try:
            max_fd = min(os.sysconf("SC_OPEN_MAX"), 4096)
        except (AttributeError, ValueError, OSError):
            max_fd = 1024
        for fd in range(3, max_fd):
            try:
                os.set_inheritable(fd, False)
            except OSError:
                pass
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception:
        logging.exception("Web-requested restart failed")
        global restart_pending
        with restart_lock:
            restart_pending = False

@app.post("/api/restart")
def api_restart_monitor():
    global restart_pending
    with restart_lock:
        if restart_pending:
            return jsonify({"ok": True, "restarting": True, "already_pending": True})
        restart_pending = True

    # Return the HTTP response first; then replace the process.
    threading.Thread(target=_restart_process_after_delay, name="web-restart", daemon=True).start()
    return jsonify({"ok": True, "restarting": True})

@app.get("/api/restart/status")
def api_restart_status():
    with restart_lock:
        return jsonify({"restarting": bool(restart_pending)})

@app.get("/")
def dashboard():
    return render_template("dashboard.html")


def short_term_diagnostics(target_name):
    m1 = recent_window_metrics(target_name, 60) or {}
    m5 = recent_window_metrics(target_name, 300) or {}
    m15 = recent_window_metrics(target_name, 900) or {}
    return {
        "loss_1m": m1.get("packet_loss"), "loss_5m": m5.get("packet_loss"), "loss_15m": m15.get("packet_loss"),
        "p50_15m": m15.get("p50_latency"), "p95_15m": m15.get("p95_latency"), "p99_15m": m15.get("p99_latency"),
        "jitter_5m": m5.get("jitter"), "avg_latency_5m": m5.get("avg_latency")
    }



def prediction_stats(row):
    """Interpretable 15-minute stability forecast from recent loss, tail latency and anomaly state.
    This is a heuristic risk estimate, not a machine-learning probability.
    """
    health = row.get("health_score")
    score = 92.0 if health is None else float(health)
    reasons = []

    if not bool(row.get("online")):
        score = min(score, 8.0)
        reasons.append("currently offline")

    loss1 = row.get("loss_1m")
    loss5 = row.get("loss_5m")
    loss15 = row.get("loss_15m")
    for value, weight, label in ((loss1, 1.8, "1m loss"), (loss5, 1.1, "5m loss"), (loss15, .55, "15m loss")):
        if value is not None and float(value) > 0:
            score -= min(25.0, float(value) * weight)
            if float(value) >= 2:
                reasons.append(f"{float(value):.1f}% {label}")

    # A worsening short-term loss trend is more predictive than an old isolated drop.
    if loss1 is not None and loss5 is not None and float(loss1) > float(loss5) + 2.0:
        score -= 8.0
        reasons.append("packet loss is rising")

    baseline = row.get("baseline_latency_ms")
    p95 = row.get("p95_15m")
    if baseline not in (None, 0) and p95 is not None:
        ratio = float(p95) / max(float(baseline), .1)
        if ratio >= 4:
            score -= 24
            reasons.append("p95 far above baseline")
        elif ratio >= 2.5:
            score -= 14
            reasons.append("p95 above baseline")
        elif ratio >= 1.7:
            score -= 6

    anomaly = str(row.get("anomaly_level") or "NORMAL").upper()
    anomaly_penalty = {"ELEVATED": 6, "HIGH": 16, "SEVERE": 30}.get(anomaly, 0)
    score -= anomaly_penalty
    if anomaly_penalty:
        reasons.append(f"{anomaly.lower()} anomaly")

    failures = int(row.get("failure_window_failures") or 0)
    threshold = max(1, int(row.get("failure_threshold") or 3))
    if failures:
        score -= min(24.0, failures / threshold * 18.0)
        reasons.append(f"{failures} recent failed check{'s' if failures != 1 else ''}")

    score = int(round(max(0.0, min(100.0, score))))
    risk = 100 - score
    if score >= 90:
        grade, level = "STABLE", "stable"
    elif score >= 75:
        grade, level = "LOW RISK", "low"
    elif score >= 55:
        grade, level = "WATCH", "watch"
    elif score >= 35:
        grade, level = "ELEVATED RISK", "elevated"
    else:
        grade, level = "HIGH RISK", "high"

    checks = int(row.get("failure_window_checks") or 0)
    confidence = min(100, max(25, 35 + checks * 8))
    if row.get("p95_15m") is not None:
        confidence = min(100, confidence + 15)
    if row.get("baseline_samples") is not None and int(row.get("baseline_samples") or 0) >= BASELINE_MIN_SAMPLES:
        confidence = min(100, confidence + 15)

    return {
        "prediction_score_15m": score,
        "prediction_risk_15m": risk,
        "prediction_grade_15m": grade,
        "prediction_level_15m": level,
        "prediction_confidence": confidence,
        "prediction_summary": ", ".join(dict.fromkeys(reasons)) if reasons else "No short-term instability signals",
    }


def summary_events(conn):
    cutoff_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).astimezone().isoformat(timespec="seconds")
    outages_24h = conn.execute(
        "SELECT COUNT(*) AS n FROM events WHERE category='OFFLINE' AND observed_at>=?", (cutoff_24h,)
    ).fetchone()["n"]
    last_state = conn.execute(
        "SELECT target, observed_at, category, detail FROM events WHERE category IN ('OFFLINE','ONLINE','RECOVERED') ORDER BY id DESC LIMIT 1"
    ).fetchone()
    outage = conn.execute(
        "SELECT id,target,observed_at,detail FROM events WHERE category='OFFLINE' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    last_outage = None
    if outage:
        recovery = conn.execute(
            "SELECT observed_at,detail FROM events WHERE target=? AND category IN ('ONLINE','RECOVERED') AND id>? ORDER BY id ASC LIMIT 1",
            (outage['target'], outage['id'])
        ).fetchone()
        duration_seconds = None
        if recovery:
            try:
                duration_seconds = max(0, int((datetime.fromisoformat(recovery['observed_at']) - datetime.fromisoformat(outage['observed_at'])).total_seconds()))
            except Exception:
                pass
        last_outage = {
            "target": outage['target'], "started_at": outage['observed_at'], "detail": outage['detail'],
            "recovered_at": recovery['observed_at'] if recovery else None,
            "duration_seconds": duration_seconds, "active": recovery is None
        }
    return {"outages_24h": int(outages_24h or 0), "last_state_change": dict(last_state) if last_state else None, "last_outage": last_outage}

@app.get("/api/status")
def api_status():
    return jsonify(build_status())


def build_status():
    groups_order = _configured_groups()
    with closing(db_connect()) as conn:
        states = {r["target"]: dict(r) for r in conn.execute("SELECT * FROM target_state").fetchall()}
        result = []
        for t in TARGETS:
            endpoint = target_display(t)
            kind = "http" if target_url(t) else "host"
            row = states.get(t["name"], {
                "target": t["name"], "host": endpoint, "tcp_port": t.get("tcp_port"), "online": 0,
                "check_kind": kind, "http_status": None,
                "verify_ssl": int(bool(t.get("verify_ssl", True))) if kind == "http" else None,
            })
            row.update(metrics_for_cached(t["name"]))
            ss = startup_status_for(t["name"])
            row["startup_verified"] = bool(ss.get("verified", False))
            row["startup_checks"] = int(ss.get("checks", 0))
            row["startup_successes"] = int(ss.get("successes", 0))
            row["startup_failures"] = int(ss.get("failures", 0))
            row["startup_last_raw_ok"] = ss.get("last_raw_ok")
            row["startup_last_error"] = ss.get("last_error")
            row["startup_verified_at"] = ss.get("verified_at")
            if not row["startup_verified"]:
                row["stability_confirmed"] = 0
            health = experience_score(
                row.get("check_kind", kind), bool(row.get("online")), row.get("uptime_24h"),
                row.get("avg_latency_24h"), row.get("jitter_24h"), row.get("consecutive_failures", 0)
            )
            row.update(short_term_diagnostics(t["name"]))
            with baseline_lock:
                diag = dict(current_diagnostics.get(t["name"], {}))
            for k,v in diag.items():
                if v is not None or k not in row:
                    row[k] = v
            score = health["score"]
            anomaly = str(row.get("anomaly_level") or "NORMAL").upper()
            if score is not None:
                if anomaly == "SEVERE": score = min(score, 45)
                elif anomaly == "HIGH": score = min(score, 65)
                elif anomaly == "ELEVATED": score = min(score, 82)
                loss5 = row.get("loss_5m")
                if loss5 is not None and loss5 >= 20: score = min(score, 45)
                elif loss5 is not None and loss5 >= 5: score = min(score, 70)
            row["health_score"] = score
            if score is None:
                row["health_grade"], row["health_level"] = health["grade"], health["level"]
            elif score >= 90: row["health_grade"], row["health_level"] = "EXCELLENT", "excellent"
            elif score >= 75: row["health_grade"], row["health_level"] = "GOOD", "good"
            elif score >= 55: row["health_grade"], row["health_level"] = "FAIR", "fair"
            elif score >= 35: row["health_grade"], row["health_level"] = "POOR", "poor"
            else: row["health_grade"], row["health_level"] = "CRITICAL", "critical"
            extra=[]
            if anomaly in ("ELEVATED","HIGH","SEVERE"): extra.append(f"{anomaly.lower()} latency anomaly")
            if row.get("loss_5m") is not None and row["loss_5m"] > 0: extra.append(f"{row['loss_5m']:.2f}% loss / 5m")
            row["health_summary"] = ", ".join(extra[:2]) if extra else health["summary"]
            row.update(prediction_stats(row))
            row["group"] = str(t.get("group", "Ungrouped")).strip() or "Ungrouped"
            try:
                row["group_index"] = groups_order.index(row["group"])
            except ValueError:
                row["group_index"] = len(groups_order)
            mcfg = monitoring_settings_for(t)
            row["failure_threshold"] = int(mcfg.get("failure_threshold", DEFAULT_FAILURE_THRESHOLD))
            row["failure_window_size"] = int(mcfg.get("failure_window_checks", DEFAULT_FAILURE_WINDOW))
            row["tls_expiry_warning_days"] = float(mcfg.get("tls_expiry_warning_days", 30))
            # Do not take alert_lock here: it is held during SMTP sends (up to the SMTP
            # timeout) and would freeze the dashboard while an e-mail is being delivered.
            try:
                ar = dict(alert_runtime.get(t["name"], {}))
            except RuntimeError:
                ar = {}
            row["alert_condition_active"] = bool(ar.get("condition_active", 0))
            row["alert_sent"] = bool(ar.get("alert_sent", 0))
            row["alert_condition_since"] = ar.get("condition_since")
            row["alert_recovering_since"] = ar.get("recovering_since")
            row["alert_escalated_at"] = ar.get("escalated_at")
            maint, maint_label = maintenance_status(t)
            row["maintenance_active"] = bool(maint)
            row["maintenance_label"] = maint_label
            blockers = dependency_blockers(t)
            row["depends_on"] = t.get("depends_on", [])
            row["dependency_blockers"] = blockers
            row["alert_suppressed"] = bool(maint or blockers)
            row["alert_suppression_reason"] = (f"maintenance: {maint_label}" if maint else ("dependency unavailable: " + ", ".join(blockers) if blockers else None))
            flap, flap_count, flap_window, flap_threshold, _ = flapping_status(t)
            row["flapping"] = flap
            row["flap_transitions"] = flap_count
            row["flap_window_seconds"] = flap_window
            row["flap_threshold"] = flap_threshold
            row["expected_status"] = t.get("expected_status")
            row["content_validation"] = bool(t.get("expected_body_contains") is not None or t.get("expected_body_regex") is not None or t.get("forbidden_body_contains") is not None)
            ph=path_health_for(t["name"])
            row["path_health_score"]=ph.get("score")
            row["path_health_level"]=ph.get("level","LEARNING")
            row["path_health_loss_percent"]=ph.get("loss_percent")
            row["path_health_jitter_ms"]=ph.get("jitter_ms")
            row["path_health_avg_ms"]=ph.get("avg_ms")
            row["path_health_baseline_ratio"]=ph.get("baseline_ratio")
            row["path_health_reasons"]=ph.get("reasons",[])
            row["path_health_observed_at"]=ph.get("observed_at")
            result.append(row)
        # Correlate peers in the same configured group. This is evidence of a shared path issue,
        # not a claim that the switch hardware itself has failed.
        for row in result:
            peers=[x for x in result if x.get("group")==row.get("group") and x.get("target")!=row.get("target")]
            affected=[x for x in peers if (x.get("loss_5m") or 0)>=5 or x.get("path_health_level") in ("DEGRADING","CRITICAL") or not bool(x.get("online"))]
            row["path_group_peers"]=len(peers)
            row["path_group_affected"]=len(affected)
            if row.get("path_health_level") in ("DEGRADING","CRITICAL") and len(affected)>=2:
                row["path_suspected_shared_issue"]=True
                row["path_health_reasons"]=(row.get("path_health_reasons") or [])+[f"{len(affected)} correlated peers affected in {row.get('group')}"]
            else:
                row["path_suspected_shared_issue"]=False
        summary = summary_events(conn)
        predicted = [x.get("prediction_score_15m") for x in result if x.get("prediction_score_15m") is not None]
        summary["prediction"] = {
            "score_15m": int(round(sum(predicted) / len(predicted))) if predicted else None,
            "at_risk_targets": sum(1 for x in predicted if x < 75),
            "high_risk_targets": sum(1 for x in predicted if x < 55),
            "total_targets": len(result)
        }
        verified_count = sum(1 for x in result if x.get("startup_verified"))
        summary["reconciliation"] = {
            "active": verified_count < len(result),
            "verified": verified_count,
            "total": len(result),
            "checking": max(0, len(result) - verified_count),
            "started_at": datetime.fromtimestamp(startup_started_at, timezone.utc).astimezone().isoformat(timespec="seconds"),
            "age_seconds": int(max(0, time.time() - startup_started_at))
        }
        summary["collector"] = collector_status()
    return {"targets": result, "summary": summary, "poll_interval_seconds": POLL_INTERVAL,
            "sample_interval_seconds": SAMPLE_INTERVAL, "version": APP_VERSION,
            "alerts_enabled": ALERTS_ENABLED}


@app.get("/api/events")
def api_events():
    limit = _int_arg("limit", 100, 1, 1000)
    target = request.args.get("target")
    with closing(db_connect()) as conn:
        if target:
            rows = conn.execute("SELECT * FROM events WHERE target=? ORDER BY id DESC LIMIT ?", (target, limit)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return jsonify([dict(r) for r in rows])


def history_range_seconds(range_name):
    ranges = {
        "1h": 3600,
        "6h": 6 * 3600,
        "24h": 24 * 3600,
        "7d": 7 * 86400,
        "30d": 30 * 86400,
    }
    return ranges.get(range_name, 24 * 3600)


def aggregate_history(rows, range_seconds):
    # Keep charts responsive when polling every few seconds. Recent ranges retain
    # more detail while older ranges are averaged into sensible time buckets.
    if range_seconds <= 3600:
        bucket_seconds = 10
    elif range_seconds <= 6 * 3600:
        bucket_seconds = 30
    elif range_seconds <= 24 * 3600:
        bucket_seconds = 120
    elif range_seconds <= 7 * 86400:
        bucket_seconds = 900
    else:
        bucket_seconds = 3600

    buckets = {}
    for row in rows:
        try:
            dt = datetime.fromisoformat(row["observed_at"])
            ts = dt.timestamp()
        except (TypeError, ValueError):
            continue
        key = int(ts // bucket_seconds) * bucket_seconds
        b = buckets.setdefault(key, {
            "checks": 0, "online": 0, "latencies": [], "statuses": {}, "kind": row["check_kind"],
            "dns": [], "tcp": [], "tls": [], "server": []
        })
        if not int(row["maintenance"] or 0):
            b["checks"] += 1
            b["online"] += int(row["online"])
        if row["latency_ms"] is not None:
            b["latencies"].append(float(row["latency_ms"]))
        for col, keyname in (("dns_ms", "dns"), ("tcp_connect_ms", "tcp"), ("tls_ms", "tls"), ("server_response_ms", "server")):
            if row[col] is not None:
                b[keyname].append(float(row[col]))
        if row["http_status"] is not None:
            status = str(row["http_status"])
            b["statuses"][status] = b["statuses"].get(status, 0) + 1

    result = []
    for ts in sorted(buckets):
        b = buckets[ts]
        lat = b["latencies"]
        status = None
        if b["statuses"]:
            status = int(max(b["statuses"], key=b["statuses"].get))
        result.append({
            "observed_at": datetime.fromtimestamp(ts, timezone.utc).astimezone().isoformat(timespec="seconds"),
            "availability": round(b["online"] * 100.0 / b["checks"], 3) if b["checks"] else 100.0,
            "latency_ms": round(sum(lat) / len(lat), 2) if lat else None,
            "min_latency_ms": round(min(lat), 2) if lat else None,
            "max_latency_ms": round(max(lat), 2) if lat else None,
            "p95_latency_ms": round(percentile(lat, .95), 2) if lat else None,
            "p99_latency_ms": round(percentile(lat, .99), 2) if lat else None,
            "http_status": status,
            "checks": b["checks"],
            "check_kind": b["kind"],
            "dns_ms": round(sum(b["dns"]) / len(b["dns"]), 2) if b["dns"] else None,
            "tcp_connect_ms": round(sum(b["tcp"]) / len(b["tcp"]), 2) if b["tcp"] else None,
            "tls_ms": round(sum(b["tls"]) / len(b["tls"]), 2) if b["tls"] else None,
            "server_response_ms": round(sum(b["server"]) / len(b["server"]), 2) if b["server"] else None,
        })
    return result, bucket_seconds


@app.get("/api/history/<path:target>")
def api_history(target):
    range_name = request.args.get("range", "24h")
    range_seconds = history_range_seconds(range_name)
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=range_seconds)).astimezone().isoformat(timespec="seconds")
    with closing(db_connect()) as conn:
        rows = conn.execute(
            "SELECT observed_at,online,latency_ms,http_status,check_kind,dns_ms,tcp_connect_ms,tls_ms,server_response_ms,maintenance FROM samples WHERE target=? AND observed_at>=? ORDER BY id",
            (target, cutoff),
        ).fetchall()
        events = conn.execute(
            "SELECT observed_at,category,detail FROM events WHERE target=? AND observed_at>=? ORDER BY id",
            (target, cutoff),
        ).fetchall()
    points, bucket_seconds = aggregate_history(rows, range_seconds)
    raw_latencies = [float(r["latency_ms"]) for r in rows if r["latency_ms"] is not None]
    sla_rows = [r for r in rows if not int(r["maintenance"] or 0)]
    raw_checks = len(sla_rows); raw_online = sum(int(r["online"]) for r in sla_rows)
    return jsonify({
        "target": target,
        "range": range_name,
        "bucket_seconds": bucket_seconds,
        "points": points,
        "summary": {
            "checks": raw_checks,
            "packet_loss": round((raw_checks-raw_online)*100.0/raw_checks,3) if raw_checks else None,
            "p50_latency_ms": round(percentile(raw_latencies,.50),2) if raw_latencies else None,
            "p95_latency_ms": round(percentile(raw_latencies,.95),2) if raw_latencies else None,
            "p99_latency_ms": round(percentile(raw_latencies,.99),2) if raw_latencies else None
        },
        "events": [dict(r) for r in events],
    })


def _int_arg(name, default, lo, hi):
    try:
        return max(lo, min(hi, int(request.args.get(name, default))))
    except (TypeError, ValueError):
        return default


@app.get("/api/samples/<path:target>")
def api_samples(target):
    # Backwards-compatible raw-sample endpoint for short periods.
    minutes = _int_arg("minutes", 60, 1, 1440)
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).astimezone().isoformat(timespec="seconds")
    with closing(db_connect()) as conn:
        rows = conn.execute("SELECT observed_at,online,latency_ms,http_status,check_kind,dns_ms,tcp_connect_ms,tls_ms,server_response_ms,maintenance FROM samples WHERE target=? AND observed_at>=? ORDER BY id", (target, cutoff)).fetchall()
    return jsonify([dict(r) for r in rows])


@app.post("/api/reset")
def api_reset():
    with db_write_lock:
        with closing(db_connect()) as conn:
            conn.execute("DELETE FROM samples")
            conn.execute("DELETE FROM events")
            conn.execute("DELETE FROM alert_state")
            conn.execute("UPDATE target_state SET total_checks=0,total_failures=0,total_state_changes=0,consecutive_failures=0,first_observed_at=?", (now_iso(),))
            conn.commit()
    with stats_lock:
        rolling_minutes.clear(); current_minute.clear(); recent_checks.clear(); last_sample_persist.clear()
    with stability_lock:
        stability_runtime.clear()
    with baseline_lock:
        baseline_runtime.clear(); current_diagnostics.clear()
    with alert_lock:
        alert_runtime.clear()
    with state_runtime_lock:
        latest_target_state.clear()
    with flap_lock:
        flap_runtime.clear(); flap_active.clear()
    return jsonify({"ok": True})


def collector_status():
    last = collector_heartbeat.get("last_sweep_at")
    age = None if last is None else max(0.0, time.time() - last)
    # Healthy when the last sweep finished recently relative to the poll interval.
    stale_after = max(30.0, POLL_INTERVAL * 5 + HTTP_TIMEOUT + PING_TIMEOUT)
    return {"running": last is not None and age <= stale_after,
            "last_sweep_at": datetime.fromtimestamp(last, timezone.utc).astimezone().isoformat(timespec="seconds") if last else None,
            "last_sweep_age_seconds": None if age is None else round(age, 1),
            "last_sweep_duration_seconds": collector_heartbeat.get("last_sweep_seconds"),
            "sweeps": collector_heartbeat.get("sweeps", 0)}


@app.get("/healthz")
def healthz():
    """Liveness for external watchdogs: 200 when the collector is sweeping, 503 otherwise."""
    st = collector_status()
    db_ok = True
    try:
        with closing(db_connect()) as conn:
            conn.execute("SELECT 1").fetchone()
    except Exception:
        db_ok = False
    started_recently = (time.time() - startup_started_at) < 30
    ok = db_ok and (st["running"] or started_recently)
    return jsonify({"ok": ok, "version": APP_VERSION, "database": db_ok, "collector": st,
                    "targets": len(TARGETS)}), (200 if ok else 503)


def _prom_escape(value):
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


@app.get("/metrics")
def prometheus_metrics():
    """Prometheus text exposition of the current per-target state."""
    data = build_status()
    series = [
        ("ipmon_target_up", "gauge", "1 when the debounced (confirmed) state is online", lambda r: 1 if r.get("online") else 0),
        ("ipmon_target_raw_ok", "gauge", "1 when the latest single check succeeded", lambda r: 1 if r.get("raw_ok") else 0),
        ("ipmon_target_latency_ms", "gauge", "Latest response time in milliseconds", lambda r: r.get("latency_ms")),
        ("ipmon_target_p95_latency_15m_ms", "gauge", "p95 response over 15 minutes", lambda r: r.get("p95_15m")),
        ("ipmon_target_loss_5m_percent", "gauge", "Failed checks over 5 minutes", lambda r: r.get("loss_5m")),
        ("ipmon_target_uptime_24h_percent", "gauge", "Availability over 24 hours", lambda r: r.get("uptime_24h")),
        ("ipmon_target_health_score", "gauge", "Stability / UX score 0-100", lambda r: r.get("health_score")),
        ("ipmon_target_prediction_score_15m", "gauge", "Predicted stability next 15 minutes 0-100", lambda r: r.get("prediction_score_15m")),
        ("ipmon_target_path_health_score", "gauge", "Active path health score 0-100", lambda r: r.get("path_health_score")),
        ("ipmon_target_tls_days_left", "gauge", "Days until TLS certificate expiry", lambda r: r.get("tls_days_left")),
        ("ipmon_target_maintenance", "gauge", "1 while in a maintenance window", lambda r: 1 if r.get("maintenance_active") else 0),
        ("ipmon_target_flapping", "gauge", "1 while flapping", lambda r: 1 if r.get("flapping") else 0),
        ("ipmon_target_checks_total", "counter", "Checks performed since last reset", lambda r: r.get("total_checks")),
        ("ipmon_target_failures_total", "counter", "Failed checks since last reset", lambda r: r.get("total_failures")),
    ]
    lines = []
    for metric, kind, help_text, getter in series:
        lines.append(f"# HELP {metric} {help_text}")
        lines.append(f"# TYPE {metric} {kind}")
        for row in data["targets"]:
            value = getter(row)
            if value is None:
                continue
            labels = f'target="{_prom_escape(row.get("target"))}",group="{_prom_escape(row.get("group"))}",kind="{_prom_escape(row.get("check_kind") or "host")}"'
            lines.append(f"{metric}{{{labels}}} {float(value):g}")
    summary = data.get("summary") or {}
    lines += ["# HELP ipmon_outages_24h Confirmed outages in the last 24 hours", "# TYPE ipmon_outages_24h gauge",
              f"ipmon_outages_24h {int(summary.get('outages_24h') or 0)}",
              "# HELP ipmon_collector_running 1 when the collector loop is sweeping", "# TYPE ipmon_collector_running gauge",
              f"ipmon_collector_running {1 if (summary.get('collector') or {}).get('running') else 0}"]
    return Response("\n".join(lines) + "\n", mimetype="text/plain; version=0.0.4")


@app.get("/api/export/<path:target>")
def api_export_csv(target):
    """Raw stored samples for one target as CSV (Excel-friendly, UTF-8 with BOM)."""
    if target.lower().endswith(".csv"):
        target = target[:-4]
    range_name = request.args.get("range", "24h")
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=history_range_seconds(range_name))).astimezone().isoformat(timespec="seconds")
    cols = ["observed_at", "online", "latency_ms", "ping_ok", "tcp_ok", "http_status", "dns_ms", "tcp_connect_ms",
            "tls_ms", "server_response_ms", "maintenance", "error"]
    with closing(db_connect()) as conn:
        rows = conn.execute(f"SELECT {','.join(cols)} FROM samples WHERE target=? AND observed_at>=? ORDER BY id",
                            (target, cutoff)).fetchall()
    buf = io.StringIO()
    buf.write("﻿")
    writer = csv.writer(buf)
    writer.writerow(["target"] + cols)
    for r in rows:
        writer.writerow([target] + [r[c] for c in cols])
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", target) or "target"
    return Response(buf.getvalue(), mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{safe}_{range_name}.csv"'})


@app.post("/api/alerts/test")
def api_alert_test():
    """Send a test e-mail with the current SMTP configuration (works even when alerts are disabled)."""
    smtp_cfg = EMAIL_ALERTS.get("smtp", {}) or {}
    if not str(smtp_cfg.get("host", "")).strip():
        return jsonify({"ok": False, "error": "email_alerts.smtp.host is not configured in config.json"}), 400
    dummy = {"name": "TEST", "host": socket.gethostname(), "group": "—"}
    lines = ["This is a test message from IP Stability Monitor.", "",
             f"Monitor host: {socket.gethostname()}", f"Version: {APP_VERSION}",
             f"Monitored targets: {len(TARGETS)}", f"Alerts enabled: {ALERTS_ENABLED}", "", f"Sent: {now_iso()}"]
    ok = send_alert_email(dummy, "[TEST] IP Stability Monitor e-mail check", lines)
    if ok:
        with db_write_lock, closing(db_connect()) as conn:
            conn.execute("INSERT INTO events(target,observed_at,category,detail) VALUES(?,?,?,?)",
                         ("monitor", now_iso(), "ALERT_TEST", "Test e-mail sent"))
            conn.commit()
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "SMTP send failed — see the monitor log for details"}), 502


def _serve():
    """Prefer the production-grade waitress server when installed; fall back to Flask's server."""
    for attempt in range(20):
        try:
            try:
                from waitress import serve
            except ImportError:
                logging.info("waitress not installed; using the built-in Flask server")
                app.run(host=LISTEN_HOST, port=LISTEN_PORT, debug=False, threaded=True, use_reloader=False)
            else:
                logging.info("Serving dashboard on http://%s:%s (waitress)", LISTEN_HOST, LISTEN_PORT)
                serve(app, host=LISTEN_HOST, port=LISTEN_PORT, threads=16, ident="IP-Stability-Monitor")
            return
        except (OSError, SystemExit) as exc:
            # After a web restart the previous process may still hold the port for a moment.
            if attempt == 19:
                raise
            os.environ.pop("WERKZEUG_SERVER_FD", None)
            logging.warning("Port %s not available yet (%s); retrying", LISTEN_PORT, exc)
            time.sleep(0.5)


if __name__ == "__main__":
    logging.info("IP Stability Monitor %s starting (config: %s, database: %s)", APP_VERSION, CONFIG_PATH, DB_PATH)
    apply_runtime_config()
    validate_targets()
    init_db()
    load_monitoring_runtime()
    _load_alert_runtime_once()
    thread = threading.Thread(target=collector_loop, name="collector", daemon=True)
    thread.start()
    path_thread = threading.Thread(target=path_health_loop, name="path-health", daemon=True)
    path_thread.start()
    try:
        _serve()
    finally:
        stop_event.set()
