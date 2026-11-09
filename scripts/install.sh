#!/usr/bin/env bash
set -euo pipefail
SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAME="$(basename "$SOURCE")"
UNINSTALL=0
if [ "${1:-}" = "--uninstall" ]; then UNINSTALL=1; shift; fi
TARGET="${1:-}"
if [ -z "$TARGET" ]; then
  for candidate in "$HOME/.claude/skills" "$HOME/.codex/skills"; do
    if [ -d "$(dirname "$candidate")" ]; then TARGET="$candidate"; break; fi
  done
fi
if [ -z "$TARGET" ]; then
  echo "No ~/.claude/skills or ~/.codex/skills found; pass a target directory." >&2
  exit 1
fi
mkdir -p "$TARGET"
DEST="$TARGET/$NAME"
if [ "$UNINSTALL" -eq 1 ]; then
  [ -L "$DEST" ] && rm "$DEST" && echo "removed $DEST"
  exit 0
fi
if [ -e "$DEST" ] && [ ! -L "$DEST" ]; then
  echo "$DEST exists and is not a symlink; not overwriting." >&2
  exit 1
fi
ln -sfn "$SOURCE" "$DEST"
echo "linked $DEST -> $SOURCE"
