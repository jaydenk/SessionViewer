#!/usr/bin/env bash
set -euo pipefail

# Load .env if it exists
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

# Generate docker-compose.override.yml with project directory mounts
OVERRIDE_FILE="docker-compose.override.yml"

PROJECT_DIRS="${PROJECT_DIRS:-}"

cat > "$OVERRIDE_FILE" <<EOF
# Auto-generated — do not edit manually
# Add project directories to PROJECT_DIRS in .env instead
services:
  backend:
    volumes:
EOF

if [ -n "$PROJECT_DIRS" ]; then
  IFS=',' read -ra DIRS <<< "$PROJECT_DIRS"
  for dir in "${DIRS[@]}"; do
    # Expand ~ and env vars
    expanded=$(eval echo "$dir")
    if [ -d "$expanded" ]; then
      echo "      - ${expanded}:${expanded}:ro" >> "$OVERRIDE_FILE"
    else
      echo "Warning: PROJECT_DIRS path not found, skipping: $expanded" >&2
    fi
  done
else
  echo "      [] # no project dirs configured" >> "$OVERRIDE_FILE"
fi

echo "Building and starting Session Viewer..."
docker compose build
docker compose up -d

echo ""
echo "Session Viewer is running at http://localhost:${PORT:-3000}"
echo "To stop: docker compose down"
