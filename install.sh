#!/bin/zsh
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PYTHON="${PYTHON:-$(command -v python3 || true)}"

if [[ -z "$PYTHON" ]]; then
  echo "Python 3 was not found. Install Python 3.11+ first, then rerun this script."
  exit 1
fi

APP="$HOME/Library/Application Support/SEED/app"
DATA="$HOME/Library/Application Support/SEED"
AGENTS="$HOME/Library/LaunchAgents"
PLIST="$AGENTS/local.seed.organism.plist"

mkdir -p "$APP" "$DATA" "$AGENTS"
rsync -a --delete --exclude "__pycache__" "$HERE/" "$APP/"

cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>local.seed.organism</string>

  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON</string>
    <string>$APP/main.py</string>
  </array>

  <key>WorkingDirectory</key>
  <string>$APP</string>

  <key>EnvironmentVariables</key>
  <dict>
    <key>SEED_HOME</key>
    <string>$DATA</string>
  </dict>

  <key>RunAtLoad</key>
  <true/>

  <key>StandardOutPath</key>
  <string>$DATA/seed.log</string>
  <key>StandardErrorPath</key>
  <string>$DATA/seed.err.log</string>
</dict>
</plist>
PLIST

chmod 600 "$PLIST"
launchctl bootout "gui/$(id -u)/local.seed.organism" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl kickstart "gui/$(id -u)/local.seed.organism"

echo "SEED installed and awakened."
echo "Status: $PYTHON '$APP/seedctl.py' status"
echo "Logs:   tail -f '$DATA/seed.log'"
echo "Stop:   launchctl bootout gui/$(id -u)/local.seed.organism"
