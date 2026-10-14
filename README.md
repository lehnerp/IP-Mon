# IP Stability Monitor

A self-hosted dashboard that watches LAN hosts, network devices and websites and tells you not only *whether* they are up, but *how stable* they are: debounced outage detection, packet loss, latency percentiles, an adaptive per-target baseline, active path-quality probes, a 15-minute stability forecast, maintenance windows, dependency-aware e-mail alerts, EN/CZ interface.

Runs on **Windows** and **Linux** (also macOS) with Python 3.9+ and a single dependency (Flask). History is stored in SQLite.

---

## Quick start

### Windows

1. Install Python 3.9+ from python.org (tick **Add python.exe to PATH**).
2. Double-click **`start_monitor.bat`**.
   - It creates a `venv`, installs the requirements, creates a starter `config.json` (this computer, two public DNS servers and a website), starts the monitor and opens <http://localhost:8096> in your browser.
   - Replace the starter targets with your own in **Settings → Targets & Groups**. Restarts from the dashboard are handled automatically.

If other computers should open the dashboard, allow inbound TCP 8096 in Windows Defender Firewall.

### Linux

```bash
sudo mkdir -p /opt/ip_stability_monitor && sudo cp -r . /opt/ip_stability_monitor
cd /opt/ip_stability_monitor
cp config.example.json config.json          # then edit targets
python3 -m venv venv && venv/bin/pip install -r requirements.txt
venv/bin/python app.py                       # foreground test, Ctrl+C to stop
```

As a service:

```bash
sudo useradd --system --home /opt/ip_stability_monitor monitor
sudo chown -R monitor: /opt/ip_stability_monitor
sudo cp ip-stability-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now ip-stability-monitor
journalctl -u ip-stability-monitor -f
```

Secrets (SMTP password, dashboard password) go in `/etc/ip-stability-monitor.env`, e.g. `IPMON_SMTP_PASSWORD=...`.

**Upgrading:** keep your `config.json` and `monitor.db`; replace everything else. The database schema and new config defaults are migrated automatically (existing values are never overwritten).

---

## What the dashboard shows

| Area | Meaning |
|---|---|
| **Targets online** | Confirmed (debounced) state, not the last single check. |
| **Outages · 24 h** | Confirmed OFFLINE events from the database. |
| **Last state change / Last outage** | With date, target, duration or *ongoing*. |
| **Predicted stability · 15 min** | Average forecast score and number of at-risk / high-risk targets. |
| **Target card** | Stability/UX score, 15-minute forecast with reasons, active path health, 24 h availability/loss/latency/jitter, 1/5/15-minute loss, p95/p99, learned baseline and anomaly level, HTTP phase timing (DNS/TCP/TLS/server), TLS expiry, maintenance / dependency / flapping / alert banners. |
| **Search & Problems only** | Filter cards by name, address, group or error; *Problems only* hides everything that is perfectly healthy. |
| **Graphs** | 1 h – 30 d latency and availability, events in range, **CSV export** of raw samples. |
| **Live indicator** | `LIVE` normally, `NO CONNECTION` when the dashboard can't reach the monitor, `STALLED` when the monitor is up but its check loop has stopped. |

---

## How monitoring works

**Checks.** Host targets: one ICMP echo per poll, plus an optional TCP connect (`tcp_port`). Web targets: a real HTTP(S) GET with a hard overall deadline and per-phase timing. Any reply that isn't a genuine echo reply (e.g. Windows *Destination host unreachable*) counts as a failure. Ping output is parsed language-independently, so Czech/English Windows and Linux/macOS all work.

**Debounced outages.** A single dropped packet is loss, not an outage. A target is declared OFFLINE when `failure_threshold` of the last `failure_window_checks` fail (default 3 of 5) and RECOVERED after `recovery_success_threshold` successes.

**Startup reconciliation.** After every start the live state is unknown (`CHECKING`) until fresh evidence confirms it (default 2 successes or 3 failures). Alerts are held back for `startup_alert_grace_seconds`.

**Adaptive baseline.** A slow EWMA of latency and variance per target (default time constant 6 h) classifies the current response as NORMAL / ELEVATED / HIGH / SEVERE. Spikes are clipped so an incident doesn't redefine "normal". The baseline survives restarts.

**Active path health (hosts only).** Every `path_health_interval_seconds` (default 5 min) each host gets a short, staggered 8-packet burst. Burst loss, jitter and latency versus baseline give NORMAL / WATCH / DEGRADING / CRITICAL and PATH_DEGRADED / PATH_RECOVERED events. If several peers in the same group degrade together the card flags a **suspected shared path / switch issue** — evidence, not proof of hardware failure. This is not a bandwidth test.

**Forecast.** An interpretable heuristic (not ML) from health, recent loss and its trend, p95 vs baseline, anomaly level and recent failures, with the reasons listed on the card.

**Flapping.** `flapping_transition_threshold` confirmed state changes inside `flapping_window_seconds` (default 4 in 15 min) mark a target as flapping.

---

## Configuration (`config.json`)

Most operational settings can be changed live in **Settings → Runtime** (saved atomically, previous file kept as `config.json.bak`). Targets and groups can be edited in **Settings → Targets & Groups** (the monitor restarts to apply them). SMTP and dashboard credentials are JSON-only.

### Targets

```json
"targets": [
  {"name": "CORE-SW-01", "host": "10.0.0.1", "group": "Core"},
  {"name": "APP-01", "host": "10.0.0.101", "tcp_port": 443, "group": "Production",
   "depends_on": ["CORE-SW-01"]},
  {"name": "Portal", "url": "https://portal.example/", "group": "Web",
   "verify_ssl": true,
   "expected_status": "200-399",
   "expected_body_contains": ["Welcome"],
   "expected_body_regex": "Build\\s+[0-9]+",
   "forbidden_body_contains": ["Service Unavailable"],
   "max_body_bytes": 65536}
],
"groups": ["Core", "Production", "Web"]
```

- `expected_status`: integer, list, or range string (`"200-399"`, default).
- `depends_on`: if an upstream target is down or in maintenance, downstream alerts are suppressed (monitoring continues). Unknown dependencies and cycles are rejected.
- Per-target overrides: `"monitoring": {...}` and `"alerts": {...}`; per-group overrides under `monitoring.group_overrides` / `email_alerts.group_overrides`.

### Maintenance windows

Checks keep running, but planned downtime is excluded from outage detection, SLA/loss windows, outage events and alerts.

```json
"maintenance": {
  "timezone": "Europe/Prague",
  "windows": [
    {"days": ["sat"], "start": "22:00", "end": "23:30", "label": "Weekly maintenance"},
    {"from": "2026-11-02T20:00:00+01:00", "to": "2026-11-02T23:00:00+01:00", "label": "Firmware upgrade"}
  ]
}
```

Overnight windows (`22:00`–`02:00`) work; day names accept English and Czech (`po`, `út`, `so`, …).

### Global settings

| Key | Default | |
|---|---|---|
| `poll_interval_seconds` | 2 | Check every target this often. |
| `sample_interval_seconds` | 10 | How often a successful check is written to history (failures and state changes are always written). |
| `ping_timeout_seconds` / `http_timeout_seconds` | 1.5 / 5 | |
| `history_retention_days` | 30 | Raw samples. |
| `event_retention_days` | 365 | Event log. |
| `listen_host` / `listen_port` | 0.0.0.0 / 8096 | |
| `database` | monitor.db | |
| `ui.language` | en | Default language for new browsers (`en`/`cs`). |

`monitoring.*`: `failure_window_checks` 5, `failure_threshold` 3, `recovery_success_threshold` 3, `startup_success_checks` 2, `startup_failure_checks` 3, `startup_alert_grace_seconds` 30, `baseline_enabled` true, `baseline_time_constant_hours` 6, `baseline_min_samples` 30, `anomaly_elevated_z` / `high_z` / `severe_z` 2.5 / 4 / 6, `tls_expiry_warning_days` 30, `flapping_window_seconds` 900, `flapping_transition_threshold` 4, `path_health_*` (enabled, interval 300 s, 8 packets, loss watch/critical 5/20 %, jitter watch 5 ms, baseline ratio 2.5×).

### E-mail alerts

```json
"email_alerts": {
  "enabled": true,
  "degradation_seconds": 180,
  "recovery_seconds": 60,
  "minimum_failed_checks": 3,
  "packet_loss_above_percent": 5.0,
  "p95_latency_above_ms": 150,
  "http_p95_latency_above_ms": 1500,
  "alert_on_anomaly_levels": ["HIGH", "SEVERE"],
  "alert_on_flapping": true,
  "reminder_seconds": 0,
  "escalation_seconds": 900,
  "smtp": {
    "host": "smtp.example.com", "port": 587, "starttls": true,
    "username": "monitor@example.com", "password_env": "IPMON_SMTP_PASSWORD",
    "from": "monitor@example.com", "to": ["admin@example.com"],
    "escalation_to": ["network-lead@example.com"]
  }
}
```

A condition must persist for `degradation_seconds` before one e-mail per incident is sent; recovery must hold for `recovery_seconds`. An unresolved incident can be escalated once. Use **Settings → Send test e-mail** to verify SMTP.

### Dashboard login (optional)

```json
"auth": {"enabled": true, "username": "admin", "password_env": "IPMON_WEB_PASSWORD",
         "read_only_without_login": true}
```

Uses HTTP Basic authentication (the browser asks for the password). With `read_only_without_login: true` anyone on the network can view, but saving settings, editing targets, restart, reset and test e-mail require the login. `password` can be used instead of `password_env`. Basic auth is only as private as the network — put the monitor behind HTTPS (reverse proxy) if it's reachable beyond a trusted LAN.

---

## Integrations & API

| Endpoint | |
|---|---|
| `GET /healthz` | 200 when the check loop and database are healthy, 503 otherwise. Never requires login — point Uptime Kuma / another monitor at it. |
| `GET /metrics` | Prometheus metrics (`ipmon_target_up`, `ipmon_target_latency_ms`, `ipmon_target_loss_5m_percent`, `ipmon_target_health_score`, `ipmon_target_tls_days_left`, …). |
| `GET /api/status` | Full live state for all targets (what the dashboard uses). |
| `GET /api/events?limit=100&target=NAME` | Event log. |
| `GET /api/history/NAME?range=1h|6h|24h|7d|30d` | Aggregated history. |
| `GET /api/export/NAME.csv?range=24h` | Raw samples as CSV (opens in Excel). |
| `POST /api/alerts/test` | Send a test e-mail. |

Environment variables: `IPMON_CONFIG` (path to an alternative config file), `IPMON_SUPERVISED=1` (the restart button exits with code 3 instead of re-executing; set automatically by `start_monitor.bat`, systemd is detected on its own).

---

## Tests

```bash
python -m unittest discover -s tests -v
```

Covers ping parsing (Linux, macOS, English and Czech Windows), status matching, scoring, maintenance windows, debouncing and dependency validation.

---

## Changelog

**6.0**
- Windows support: ping works with Windows `ping.exe` in any language (previously every host check failed on Windows), no console window flashes, *Destination host unreachable* is no longer counted as success. Burst probes work on Windows and use a 0.2 s interval on Linux so they also run as a non-root user.
- Fixed the dashboard *Restart monitor* button: with current Flask/Werkzeug the restarted process couldn't bind the port and the monitor stayed down. Restart now also works under systemd and on Windows (`start_monitor.bat`).
- Fixed the *at risk / high risk* counters ignoring targets with a forecast score of 0.
- Fixed the hidden *Save targets & restart* button showing on the Runtime tab.
- The dashboard no longer freezes while an alert e-mail is being sent; a slow check can't be started twice in parallel; the collector waits for a sweep with one overall timeout.
- New: optional dashboard login, `/healthz`, Prometheus `/metrics`, CSV export, *Send test e-mail*, target search and *Problems only* filter, connection/stalled indicator, event-log retention, more settings editable in the UI (startup reconciliation, path health), clearer JSON errors on startup, waitress production server when installed, Windows launcher, hardened systemd unit, unit tests.
- Web targets no longer show an empty *Active path health* panel; total probe loss is reported as CRITICAL.

**5.x** — target & group manager, web restart, startup reconciliation, active path / switch degradation detection, dynamic configuration, maintenance windows, dependency-aware alerts, HTTP content validation, flapping detection, alert escalation, EN/CZ localisation, 15-minute forecast, responsive graphs, debounced outages, rolling loss and percentiles, adaptive baseline, TLS expiry.
