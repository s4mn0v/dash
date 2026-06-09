#!/usr/bin/env bash

ROOT="${1:-.}"
OUTPUT="${2:-project.txt}"

# Resolve absolute paths safely
SCRIPT_PATH="$(realpath "$0")"
ROOT_PATH="$(realpath "$ROOT")"
OUTPUT_PATH="$ROOT_PATH/$OUTPUT"

# Clear output file first
>"$OUTPUT_PATH"

find "$ROOT_PATH" \
  -type d \( -path "$ROOT_PATH/.git" -o -path "$ROOT_PATH/tes" \) -prune \
  -o -type f ! -path "$SCRIPT_PATH" ! -path "$OUTPUT_PATH" -print | while IFS= read -r file; do

  echo "===== FILE: $file =====" >>"$OUTPUT_PATH"
  cat "$file" >>"$OUTPUT_PATH"
  echo -e "\n" >>"$OUTPUT_PATH"

done

echo "Done. Output saved to $OUTPUT_PATH"
