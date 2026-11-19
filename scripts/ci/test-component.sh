#!/usr/bin/env bash
# Kiểm tra một thành phần của da-platform, đúng như CI chạy.
#
#   scripts/ci/test-component.sh <thành-phần>
#   scripts/ci/test-component.sh --list
#
# CI (.github/workflows/component.yaml) gọi đúng script này, nên chạy local ra
# kết quả nào thì CI ra kết quả đó. Script giả định layout meta-repo: các thư
# mục anh em (packages-ai/, ai-sdk/, service-sdk/, contracts/) nằm cạnh nhau,
# vì pyproject dùng path dependency "../<repo>" và spec core-api đọc
# ../contracts.
#
# Chạy local mà không muốn đụng .venv của mình thì đặt
# UV_PROJECT_ENVIRONMENT=/đường/dẫn/khác.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

PY="${CI_PYTHON:-3.10}"
COMPONENTS=(contracts core-api web worker packages-ai ai-sdk ai-tutor
            mcp-service embedding-service service-sdk document-inspector video-mcp)

if [ "${1:-}" = "--list" ]; then
  printf '%s\n' "${COMPONENTS[@]}"
  exit 0
fi
c="${1:?dùng: scripts/ci/test-component.sh <thành-phần> (xem --list)}"

step() { printf '\n==> [%s] %s\n' "$c" "$*"; }

# uv sync theo lockfile rồi chạy pytest; tham số thứ hai trở đi là cờ của uv sync.
uv_sync() {
  step "uv sync $*"
  uv sync --locked --python "$PY" "$@"
}
pytest_run() {
  step "pytest $*"
  uv run --no-sync pytest -q "$@"
}

case "$c" in
  contracts)
    step "contract, prompt và parser khớp nhau về shape quiz item / lesson card"
    python3 scripts/check_content_schema.py
    step "catalog model của core-api khớp catalog ai-sdk"
    python3 scripts/check_model_catalog.py
    ;;

  core-api)
    cd core-api
    step "pnpm install"
    pnpm install --frozen-lockfile
    step "prisma generate"
    pnpm exec prisma generate
    # model-catalog.ts đọc <cwd>/proto/llm_model_catalog.json; Dockerfile và
    # compose đặt contracts/proto vào đó. Ở đây chép tạm rồi dọn khi xong, để
    # chạy local không để lại thư mục lạ.
    if [ ! -e proto ]; then
      cp -R ../contracts/proto proto
      trap 'rm -rf "$ROOT/core-api/proto"' EXIT
    fi
    # Luật phụ thuộc giữa các tầng (no-restricted-imports/properties), prettier
    # và mọi luật khác đều chặn (lỗi định dạng: chạy `pnpm format`). Riêng các
    # luật dưới đây là nợ cũ (11/2026: ~540 lỗi any/unsafe) nên tạm tắt trong
    # CI; trả xong luật nào thì xóa dòng của luật đó.
    step "eslint (gồm luật phụ thuộc giữa các tầng + prettier)"
    debt_rules=(
      @typescript-eslint/no-unsafe-member-access
      @typescript-eslint/no-unsafe-assignment
      @typescript-eslint/no-unsafe-call
      @typescript-eslint/no-unsafe-return
      @typescript-eslint/require-await
      @typescript-eslint/no-unnecessary-type-assertion
      @typescript-eslint/no-base-to-string
      @typescript-eslint/no-unused-vars
      @typescript-eslint/unbound-method
      @typescript-eslint/restrict-template-expressions
    )
    rule_args=()
    for r in "${debt_rules[@]}"; do rule_args+=(--rule "$r: off"); done
    pnpm exec eslint --quiet "${rule_args[@]}" "{src,test}/**/*.ts"
    step "tsc"
    pnpm exec tsc --noEmit --incremental false
    step "jest"
    pnpm exec jest --ci
    ;;

  web)
    cd web
    step "pnpm install"
    pnpm install --frozen-lockfile
    step "tsc"
    pnpm exec tsc --noEmit --incremental false
    step "client coreApi so route hai chiều với controller core-api"
    node scripts/test-core-api.mjs
    step "LTI deep link + roles"
    node scripts/test-lti-deep-link.mjs
    node scripts/test-lti-roles.mjs
    ;;

  worker)
    cd worker
    uv_sync
    pytest_run tests/unit
    ;;

  packages-ai)
    cd packages-ai
    # Không cài extra ocr (docling, vài GB): DoclingPdfParser import lười,
    # thiếu thì chỉ trả Err, test unit không cần.
    uv_sync --extra embeddings --extra llamaindex --extra remote-embedding --extra dev
    pytest_run tests/unit
    ;;

  ai-sdk)
    cd ai-sdk
    uv_sync --extra dev
    pytest_run
    ;;

  ai-tutor)
    cd ai-tutor
    uv_sync
    pytest_run
    ;;

  mcp-service)
    cd mcp-service
    uv_sync
    pytest_run tests/unit
    ;;

  embedding-service)
    cd embedding-service
    uv_sync
    # slow = smoke test nạp BGE-M3 thật (~3 GB), không chạy trong CI.
    pytest_run tests/unit -m "not slow"
    ;;

  service-sdk)
    cd service-sdk
    uv_sync
    step "sinh lại stub gRPC và kiểm tra không lệch so với bản đã commit"
    uv run --no-sync python scripts/generate_proto.py
    git diff --exit-code -- src/da_service_sdk/generated
    pytest_run tests/unit
    ;;

  document-inspector)
    cd document-inspector
    uv_sync
    pytest_run tests/unit
    ;;

  video-mcp)
    cd video-mcp
    step "go vet"
    go vet ./...
    step "go test"
    go test ./...
    ;;

  *)
    echo "không biết thành phần '$c'; có: ${COMPONENTS[*]}" >&2
    exit 2
    ;;
esac

printf '\n==> [%s] OK\n' "$c"
