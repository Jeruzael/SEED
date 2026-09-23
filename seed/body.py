from __future__ import annotations
import os
import platform
import re
import shutil
import socket
import subprocess
import time
from pathlib import Path

def _run(*args: str) -> str:
    try:
        return subprocess.check_output(args, stderr=subprocess.DEVNULL, text=True, timeout=2).strip()
    except Exception:
        return ""

def battery_state() -> tuple[int | None, bool | None]:
    out = _run("/usr/bin/pmset", "-g", "batt")
    # Read one battery record, not incidental percentages/status words in headers.
    records = re.findall(r"^\s*-InternalBattery-\d+\b(?:\s+\(id=\d+\))?\s*(.*)$",
                         out, flags=re.IGNORECASE | re.MULTILINE)
    if len(records) != 1:
        return None, None
    fields = records[0].split(";")
    percentage = re.fullmatch(r"(\d{1,3})\s*%", fields[0].strip())
    pct = int(percentage[1]) if percentage and int(percentage[1]) <= 100 else None
    statuses = [" ".join(field.lower().split()) for field in fields[1:]]
    known = {"charging", "discharging", "not charging", "charged"}
    if not statuses or statuses[0] not in known or len(set(statuses) & known) != 1:
        return pct, None
    status = statuses[0]
    # Explicit negative status wins over an AC header (a plugged-in battery may
    # be discharging or not charging). Never match 'charging' as a substring.
    if status in ("discharging", "not charging"):
        return pct, False
    headers = re.findall(r"^\s*Now\s+drawing\s+from\s+['\"]([^'\"]+)['\"]\s*$",
                         out, flags=re.IGNORECASE | re.MULTILINE)
    powers = {" ".join(header.lower().split()) for header in headers}
    if powers == {"ac power"} or (status == "charging" and not powers):
        # 'charged' on AC preserves the legacy externally-powered meaning.
        return pct, True
    return pct, None

def network_reachable() -> bool:
    # Observation only. No data is sent beyond opening a short TCP connection.
    try:
        with socket.create_connection(("1.1.1.1", 443), timeout=1.0):
            return True
    except OSError:
        return False

class Body:
    def __init__(self, home: Path):
        self.home = home
        self.started_monotonic = time.monotonic()

    def perceive(self) -> dict:
        batt, charging = battery_state()
        usage = shutil.disk_usage(self.home)
        load1, load5, load15 = os.getloadavg()
        cpu_count = os.cpu_count() or 1
        return {
            "wall_time": time.time(),
            "local_hour": time.localtime().tm_hour,
            "battery_pct": batt,
            "charging": charging,
            "disk_free_pct": round((usage.free / usage.total) * 100, 2),
            "load_ratio": round(load1 / cpu_count, 3),
            "load_5m_ratio": round(load5 / cpu_count, 3),
            "network": network_reachable(),
            "hostname": platform.node(),
            "machine": platform.machine(),
            "macos": platform.mac_ver()[0],
        }
