#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <downloaded-binary-path> [target-dir]"
  echo "Example: $0 ./sch-ubuntu-latest"
  exit 1
fi

source_path="$1"
target_dir="${2:-$HOME/.local/bin}"
target_path="$target_dir/sch"
legacy_target_path="$target_dir/neis-cli"

if [ ! -f "$source_path" ]; then
  echo "Binary not found: $source_path"
  exit 1
fi

mkdir -p "$target_dir"
cp "$source_path" "$target_path"
chmod +x "$target_path"
ln -sf "$target_path" "$legacy_target_path"

echo "Installed: $target_path"

case ":$PATH:" in
  *":$target_dir:"*)
    echo "PATH already includes $target_dir"
    ;;
  *)
    echo "Add this to your shell profile (~/.bashrc, ~/.zshrc):"
    echo "export PATH=\"$target_dir:\$PATH\""
    ;;
esac

echo "Now you can run: sch food"
