#!/usr/bin/env python3
from pathlib import Path
import json, os, sqlite3, sys, subprocess

HOME = Path(os.environ.get("SEED_HOME", Path.home() / "Library" / "Application Support" / "SEED"))
DB = HOME / "memory.sqlite3"
LABEL = "local.seed.organism"

def status():
    if not DB.exists():
        print("SEED has no memory yet.")
        return
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    meta = {}
    for row in db.execute("SELECT key,value FROM meta"):
        try: meta[row["key"]] = json.loads(row["value"])
        except Exception: meta[row["key"]] = row["value"]
    episodes = db.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
    concepts = db.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
    print(json.dumps({
        "identity": meta.get("identity"),
        "last_wake": meta.get("last_wake"),
        "last_sleep": meta.get("last_sleep"),
        "last_action": meta.get("last_action"),
        "last_state": meta.get("last_state"),
        "episodes": episodes,
        "concepts": concepts,
    }, indent=2))

if len(sys.argv) < 2 or sys.argv[1] == "status":
    status()
elif sys.argv[1] == "tail":
    os.execvp("tail", ["tail", "-f", str(HOME / "seed.log")])
else:
    print("Usage: python3 seedctl.py [status|tail]")
