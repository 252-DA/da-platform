#!/usr/bin/env bash
# Triển khai một bản image lên VM prod.
#
#   deploy/deploy.sh <image-tag>             tag = SHA của meta-repo (CI đẩy :<sha>)
#   deploy/deploy.sh --no-backup <image-tag> bỏ bước dump (chỉ khi DB còn trống)
#
# Thứ tự: preflight → backup → pull → kho dữ liệu → migrate → db-roles →
# up -d --wait → ghi lại IMAGE_TAG → dọn image cũ.
#
# Rollback = chạy lại với SHA cũ. Migration Prisma chỉ đi một chiều: nếu
# migration làm hỏng dữ liệu thì restore từ backups/pre-<tag>-*.dump trước, rồi
# mới lùi image.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

BACKUP=1
if [ "${1:-}" = "--no-backup" ]; then
  BACKUP=0
  shift
fi
TAG="${1:?dùng: deploy/deploy.sh [--no-backup] <image-tag>}"

ENV_FILE="${ENV_FILE:-.env.prod}"
DC=(docker compose -f deploy/docker-compose.prod.yml --env-file "$ENV_FILE")

# Biến môi trường của shell thắng --env-file, nên tag mới có hiệu lực ngay cả khi
# .env.prod còn tag cũ. Chỉ ghi vào file sau khi deploy thành công.
export IMAGE_TAG="$TAG"

env_value() { grep -E "^$1=" "$ENV_FILE" | tail -n1 | cut -d= -f2-; }

echo "==> 1/7 preflight"
[ -f "$ENV_FILE" ] || { echo "thiếu $ENV_FILE (mẫu: deploy/.env.prod.example)" >&2; exit 1; }
if [ "$(stat -c %a "$ENV_FILE" 2>/dev/null || stat -f %Lp "$ENV_FILE")" != "600" ]; then
  echo "cảnh báo: $ENV_FILE nên là chmod 600" >&2
fi
KEYS_DIR_VALUE="$(env_value KEYS_DIR || true)"
# KEYS_DIR tính từ deploy/ (nơi có compose file); mặc định ../keys.
KEYS_DIR_ABS="$(cd deploy && cd "${KEYS_DIR_VALUE:-../keys}" 2>/dev/null && pwd)" \
  || { echo "không thấy thư mục khóa (${KEYS_DIR_VALUE:-../keys} tính từ deploy/)" >&2; exit 1; }
for k in lti.pem lti.pub.pem bff-to-core.pem bff-to-core.pub.pem; do
  [ -f "$KEYS_DIR_ABS/$k" ] || { echo "thiếu khóa $KEYS_DIR_ABS/$k" >&2; exit 1; }
done
"${DC[@]}" --profile ops config -q   # báo lỗi nếu thiếu biến bắt buộc

if [ "$BACKUP" = 1 ]; then
  echo "==> 2/7 backup Postgres"
  deploy/backup.sh "pre-${TAG:0:12}"
else
  echo "==> 2/7 backup: bỏ qua (--no-backup)"
fi

echo "==> 3/7 pull image $TAG"
"${DC[@]}" --profile ops pull

echo "==> 4/7 kho dữ liệu"
"${DC[@]}" up -d --wait --wait-timeout 300 postgres redis qdrant neo4j

echo "==> 5/7 migrate"
"${DC[@]}" run --rm -T migrate

echo "==> 6/7 phân quyền role Postgres"
"${DC[@]}" run --rm -T db-roles

echo "==> 7/7 khởi động ứng dụng"
if ! "${DC[@]}" up -d --remove-orphans --wait --wait-timeout 600; then
  echo >&2
  echo "deploy: có service chưa healthy. Trạng thái:" >&2
  "${DC[@]}" ps >&2 || true
  echo "Xem log: ${DC[*]} logs --tail 100 <service>" >&2
  echo "Lùi bản:  deploy/deploy.sh <sha-cũ>" >&2
  exit 1
fi

# Ghi tag đã chạy được để các lệnh compose thủ công (ps, logs, exec) dùng đúng tag.
if grep -q '^IMAGE_TAG=' "$ENV_FILE"; then
  sed -i.bak "s|^IMAGE_TAG=.*|IMAGE_TAG=${TAG}|" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
else
  printf '\nIMAGE_TAG=%s\n' "$TAG" >> "$ENV_FILE"
fi

# Image không dùng và cũ hơn 7 ngày. Bản đang chạy luôn được giữ; muốn lùi về
# bản đã bị dọn thì pull lại từ GHCR.
docker image prune -af --filter "until=168h" >/dev/null

echo
"${DC[@]}" ps
echo "deploy: xong, đang chạy $TAG"
