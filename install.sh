#!/bin/bash
# MyTeam installer — symlinks `myteam` onto your PATH. Safe to re-run.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
chmod +x "$HERE/bin/myteam" "$HERE/bin/myteam-web"

TARGET=""
for d in "$HOME/.local/bin" "$HOME/bin"; do
  case ":$PATH:" in *":$d:"*) TARGET="$d"; break;; esac
done
if [ -z "$TARGET" ]; then
  TARGET="$HOME/.local/bin"
  echo "note: $TARGET is not on your PATH — add this to your shell profile:"
  echo '  export PATH="$HOME/.local/bin:$PATH"'
fi
mkdir -p "$TARGET"
ln -sf "$HERE/bin/myteam" "$TARGET/myteam"
ln -sf "$HERE/bin/myteam-web" "$TARGET/myteam-web"
echo "✓ installed: $TARGET/myteam -> $HERE/bin/myteam"
echo "✓ installed: $TARGET/myteam-web -> $HERE/bin/myteam-web"
echo
echo "next: run  myteam   (to found your team; terminal control room)"
echo "      or   myteam-web   (the control room in your browser)"
