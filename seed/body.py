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
    match = re.search(r"(\d+)%", out)
    pct = int(match.group(1)) if match else None
    if not out:
        charging = None
    else:
        low = out.lower()
        charging = ("charging" in low) or ("ac power" in low and "discharging" not in low)
    return pct, charging

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
