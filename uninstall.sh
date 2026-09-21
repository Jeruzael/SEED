#!/bin/zsh
set -euo pipefail
PLIST="$HOME/Library/LaunchAgents/local.seed.organism.plist"
launchctl bootout "gui/$(id -u)/local.seed.organism" 2>/dev/null || true
rm -f "$PLIST"
echo "SEED startup entry removed."
echo "Its memories remain at: $HOME/Library/Application Support/SEED"
echo "Delete that folder manually only if you also want to erase its memory."
