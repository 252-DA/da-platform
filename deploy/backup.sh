#!/usr/bin/env bash
# Dump Postgres của stack prod vào backups/ (định dạng custom, nạp lại bằng pg_restore).
#
#   deploy/backup.sh [nhãn]      → backups/<nhãn>-<UTC>.dump  (nhãn mặc định: daily)
#
# Giữ KEEP bản mới nhất cho mỗi nhãn (mặc định 14). deploy/deploy.sh gọi nó với
# nhãn pre-<tag> trước mỗi lần migrate. Cron hằng ngày:
#   15 3 * * * cd /opt/da-platform && deploy/backup.sh daily
#
# Chưa làm: đẩy bản dump lên R2 (bucket backup riêng) và snapshot Qdrant/Neo4j.
# Hiện bản dump chỉ nằm trên chính VM, tức là chưa phải backup thật. Restore thử
# một lần vào DB tạm để biết nó dùng được:
#   docker compose -f deploy/docker-compose.prod.yml --env-file .env.prod exec -T postgres \
#     sh -c 'createdb -U "$POSTGRES_USER" restore_test && pg_restore -U "$POSTGRES_USER" -d restore_test --no-owner' < backups/<file>.dump
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

LABEL="${1:-daily}"
KEEP="${KEEP:-14}"
ENV_FILE="${ENV_FILE:-.env.prod}"
DC=(docker compose -f deploy/docker-compose.prod.yml --env-file "$ENV_FILE")

if ! "${DC[@]}" ps --status running --services 2>/dev/null | grep -qx postgres; then
  echo "backup: postgres chưa chạy, bỏ qua (lần deploy đầu tiên thì bình thường)."
  exit 0
fi

mkdir -p backups
chmod 700 backups
OUT="backups/${LABEL}-$(date -u +%Y%m%dT%H%M%SZ).dump"
TMP="${OUT}.partial"
trap 'rm -f "$TMP"' EXIT

# Dùng biến môi trường bên trong container nên không cần đọc .env.prod ở đây.
"${DC[@]}" exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$TMP"

if [ ! -s "$TMP" ]; then
  echo "backup: file dump rỗng, dừng." >&2
  exit 1
fi
chmod 600 "$TMP"
mv "$TMP" "$OUT"
echo "backup: đã ghi $OUT ($(du -h "$OUT" | cut -f1))"

# Xóa bản cũ của cùng nhãn, giữ KEEP bản mới nhất.
ls -1t backups/"${LABEL}"-*.dump 2>/dev/null | tail -n +"$((KEEP + 1))" | while IFS= read -r old; do
  rm -f -- "$old"
  echo "backup: đã xóa bản cũ $old"
done
