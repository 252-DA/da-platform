#!/usr/bin/env bash
# Kiểm tra web đầy đủ sau khi kênh web->core-api chuyển sang HTTP REST:
# typecheck + test client coreApi (so route hai chiều với controller core-api)
# + test LTI. Chạy trong image da-platform-web với node_modules từ volume,
# mount thêm source core-api để so route. Chạy được từ mọi thư mục.
#
# Cần: image da-platform-web đã build, volume da-platform_web_node_modules đã có.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
docker run --rm --network none \
  -v "$REPO_ROOT/web:/repo/web:ro" \
  -v da-platform_web_node_modules:/repo/web/node_modules:ro \
  -v "$REPO_ROOT/core-api/src:/repo/core-api/src:ro" \
  -w /repo/web da-platform-web sh -c \
  'npx tsc --noEmit --incremental false && node scripts/test-core-api.mjs && node scripts/test-lti-deep-link.mjs && node scripts/test-lti-roles.mjs'
