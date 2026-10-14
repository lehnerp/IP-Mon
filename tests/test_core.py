"""Unit tests for platform-independent parsing and scoring helpers.

Run from the project folder:   python -m unittest discover -s tests -v
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_tmp = tempfile.mkdtemp(prefix="ipmon-test-")
_cfg = Path(_tmp) / "config.json"
_cfg.write_text(json.dumps({"database": str(Path(_tmp) / "test.db"),
                            "targets": [{"name": "LOCAL", "host": "127.0.0.1"}]}), encoding="utf-8")
os.environ["IPMON_CONFIG"] = str(_cfg)
sys.path.insert(0, str(ROOT))
import app  # noqa: E402

LINUX = """PING 10.0.0.1 (10.0.0.1) 56(84) bytes of data.
64 bytes from 10.0.0.1: icmp_seq=1 ttl=64 time=0.412 ms
64 bytes from 10.0.0.1: icmp_seq=2 ttl=64 time=1.20 ms
64 bytes from 10.0.0.1: icmp_seq=4 ttl=64 time=0.388 ms

--- 10.0.0.1 ping statistics ---
4 packets transmitted, 3 received, 25% packet loss, time 3004ms
rtt min/avg/max/mdev = 0.388/0.666/1.200/0.380 ms
"""
WINDOWS_EN = """Pinging 10.0.0.1 with 32 bytes of data:
Reply from 10.0.0.1: bytes=32 time<1ms TTL=64
Reply from 10.0.0.1: bytes=32 time=3ms TTL=64
Request timed out.
Reply from 10.0.0.9: Destination host unreachable.

Ping statistics for 10.0.0.1:
    Packets: Sent = 4, Received = 3, Lost = 1 (25% loss),
"""
WINDOWS_CS = """Příkaz PING na 10.0.0.1 s 32 bajty dat:
Odpověď od 10.0.0.1: bajty=32 čas<1ms TTL=64
Odpověď od 10.0.0.1: bajty=32 čas=12ms TTL=64
Vypršel časový limit žádosti.

Statistika ping pro 10.0.0.1:
    Pakety: Odeslané = 3, Přijaté = 2, Ztracené = 1 (ztráta 33%),
"""
MACOS = "64 bytes from 10.0.0.1: icmp_seq=0 ttl=64 time=4.521 ms\n"


class PingParsing(unittest.TestCase):
    def test_linux(self):
        self.assertEqual(app.parse_ping_replies(LINUX), [0.412, 1.2, 0.388])

    def test_windows_english_ignores_unreachable(self):
        # "Destination host unreachable" is a reply from a router, not an echo reply.
        self.assertEqual(app.parse_ping_replies(WINDOWS_EN), [1.0, 3.0])

    def test_windows_czech(self):
        self.assertEqual(app.parse_ping_replies(WINDOWS_CS), [1.0, 12.0])

    def test_macos(self):
        self.assertEqual(app.parse_ping_replies(MACOS), [4.521])

    def test_no_reply(self):
        self.assertEqual(app.parse_ping_replies("Request timed out.\n"), [])

    def test_windows_command(self):
        old = app.IS_WINDOWS
        try:
            app.IS_WINDOWS = True
            self.assertEqual(app._ping_command("h", 1, 1.5), ["ping", "-n", "1", "-w", "1500", "h"])
        finally:
            app.IS_WINDOWS = old


class Helpers(unittest.TestCase):
    def test_status_matches(self):
        self.assertTrue(app._status_matches(204, "200-399"))
        self.assertFalse(app._status_matches(500, "200-399"))
        self.assertTrue(app._status_matches(401, [200, 401]))
        self.assertTrue(app._status_matches(301, None))

    def test_percentile(self):
        self.assertEqual(app.percentile([1, 2, 3, 4, 5], .5), 3)
        self.assertIsNone(app.percentile([], .5))

    def test_experience_score_offline_is_low(self):
        self.assertLessEqual(app.experience_score("host", False, 100, 1, 0)["score"], 18)
        self.assertGreaterEqual(app.experience_score("host", True, 100, 1, 0.5)["score"], 95)

    def test_maintenance_overnight(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        t = {"name": "X", "maintenance": {"timezone": "Europe/Prague",
             "windows": [{"days": ["sat"], "start": "22:00", "end": "02:00"}]}}
        tz = ZoneInfo("Europe/Prague")
        self.assertTrue(app.maintenance_status(t, datetime(2026, 10, 17, 23, 0, tzinfo=tz))[0])   # Sat 23:00
        self.assertTrue(app.maintenance_status(t, datetime(2026, 10, 18, 1, 30, tzinfo=tz))[0])   # Sun 01:30
        self.assertFalse(app.maintenance_status(t, datetime(2026, 10, 18, 23, 0, tzinfo=tz))[0])  # Sun 23:00

    def test_debounce_single_loss_is_not_outage(self):
        t = {"name": "DEB"}
        for _ in range(3):
            app.stability_decision(t, True)
        eff, *_ = app.stability_decision(t, False)
        self.assertTrue(eff)
        app.stability_decision(t, False)
        eff, _c, transition, *_ = app.stability_decision(t, False)
        self.assertFalse(eff)
        self.assertEqual(transition, "OFFLINE")

    def test_dependency_cycle_rejected(self):
        with self.assertRaises(ValueError):
            app._validate_target_list([{"name": "A", "host": "1", "depends_on": ["B"]},
                                       {"name": "B", "host": "2", "depends_on": ["A"]}])


if __name__ == "__main__":
    unittest.main()
