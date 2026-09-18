#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/career-dashboard"
exec "./Start Dashboard.command" "$@"
