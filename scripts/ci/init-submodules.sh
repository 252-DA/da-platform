#!/usr/bin/env bash
# Kéo các submodule cần để build/test, theo đúng gitlink đã commit.
#
#   scripts/ci/init-submodules.sh [path-bỏ-qua ...]
#
# Luôn bỏ `report` (LaTeX, không liên quan runtime, hay trỏ vào commit chưa
# push nên làm hỏng cả checkout). Path truyền thêm cũng bị bỏ qua: workflow của
# repo con dùng nó để tự đặt commit đang test vào chỗ đó.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."

skip=(report "$@")
paths=()
while read -r _ p; do
  for s in "${skip[@]}"; do
    [ "$p" = "$s" ] && continue 2
  done
  paths+=("$p")
done < <(git config -f .gitmodules --get-regexp '^submodule\..*\.path$')

# .gitmodules ghi URL SSH; runner CI không có khóa SSH, các repo đều public nên
# đi HTTPS. Dùng -c (truyền xuống tiến trình git con) thay vì --global để chạy
# local không sửa cấu hình git của máy.
git -c url."https://github.com/".insteadOf="git@github.com:" \
    -c protocol.version=2 \
    submodule update --init --depth 1 -- "${paths[@]}"
git submodule status -- "${paths[@]}"
