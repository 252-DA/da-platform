# Chạy da-platform trên máy dev (Infisical + Tailscale)

Không ai gửi file `.env` cho nhau nữa. Secret dùng chung nằm trên **Infisical**
(project `da-platform`, môi trường `dev`) và được bơm vào lúc chạy qua
`scripts/dc`. File `.env` trên máy bạn chỉ còn cấu hình riêng của máy và key
model của chính bạn.

| Nằm ở đâu | Biến / file |
|---|---|
| Infisical `dev` (dùng chung) | `DB_HOST`, `POSTGRES_*`, `REDIS_PASSWORD`, `MINIO_ROOT_*`, `NEO4J_PASSWORD`, `QDRANT_API_KEY`, `EMBEDDING_BACKEND`, `EMBEDDING_API_BASE_URL`, `EMBEDDING_API_MODEL`, `CANVAS_API_TOKEN`, `CANVAS_PUBLIC_URL`, LTI phía Canvas (`LTI_LMS_TYPE`, `LTI_PLATFORM_URL`, `LTI_ISSUER_URL`, `LTI_AUTH_URL`, `LTI_JWKS_URL`, `LTI_TOKEN_URL`, `LTI_COOKIE_*`) |
| `.env` của bạn | `COMPOSE_FILE`, port, `GEMINI_API_KEY`, `DEEPSEEK_API_KEY`, `EMBEDDING_API_KEY`, `AGS_ENABLED`, `CANVAS_AUTO_SYNC_ENABLED`, LTI phía tool (`LTI_REDIRECT_URI`, `LTI_CLIENT_ID`, `LTI_DEPLOYMENT_ID`) |
| File trên máy, không commit | `web/keys/lti.pem`, `web/keys/lti.pub.pem`, `web/keys/bff-to-core.pem`, `core-api/keys/bff-to-core.pub.pem` |

Biến nào có trên Infisical thì giá trị trong `.env` bị bỏ qua.

Hạ tầng dùng chung:

- **DB stack** (Postgres, Redis, MinIO, Qdrant, Neo4j) chạy trên máy `fedoralap`,
  `100.102.89.124`, chỉ vào được qua Tailscale.
- **Canvas** chạy trên máy của admin nhóm, public tại `https://canvas.canxphung.dev`.

---

## 1. Chuẩn bị (làm một lần)

1. **Docker Desktop** và **Node.js** (bản nào ≥ 18 cũng được, chỉ dùng để sinh khóa).
2. **Tailscale**: cài app, nhận lời mời từ admin nhóm, đăng nhập. Kiểm tra:
   ```bash
   tailscale ping 100.102.89.124
   ```
3. **Infisical**: nhận email mời, tạo tài khoản. Cài CLI rồi đăng nhập:
   ```bash
   brew install infisical/get-cli/infisical   # Linux/Windows: https://infisical.com/docs/cli/overview
   infisical login                            # chọn "Infisical Cloud (US Region)"
   ```
4. **Clone repo** kèm submodule (xem [README](../README.md#clone-lần-đầu)).
   Nếu repo chưa có file `.infisical.json` thì chạy thêm `infisical init` và
   chọn project `da-platform`.

## 2. Tạo `.env`

```bash
cp .env.team.example .env
```

Điền key model của bạn:

- `GEMINI_API_KEY`: model mặc định của hầu hết task.
- `DEEPSEEK_API_KEY`: chỉ cần cho sinh câu hỏi.
- `EMBEDDING_API_KEY`: Voyage, cần khi index tài liệu hoặc tìm kiếm.

Đây là key của riêng bạn, bạn tự trả phí, nên hãy đặt hạn mức chi tiêu ở trang
của nhà cung cấp. Phần LTI để trống nếu chưa cần launch từ Canvas (xem mục 5).

## 3. Sinh khóa

```bash
node scripts/gen_dev_keys.mjs
```

Script tạo cặp khóa LTI (RS256) và cặp khóa web → core-api (Ed25519). File nào
đã có thì script bỏ qua. Không dùng `openssl` của macOS vì nó không tạo được
khóa Ed25519.

## 4. Chạy stack

**Luôn dùng `scripts/dc` thay cho `docker compose`.** Script này lấy secret từ
Infisical rồi gọi `docker compose` với đúng tham số bạn đưa vào. Nếu gọi
`docker compose` trực tiếp, mọi lệnh, kể cả `ps` và `logs`, đều lỗi
`required variable ... is missing`.

```bash
scripts/dc up -d --build --scale cloudflared=0
scripts/dc ps
scripts/dc logs -f core-api
```

- `--scale cloudflared=0`: service `cloudflared` là tunnel của admin
  (`app.canxphung.dev`). Đừng chạy nó trên máy bạn: thiếu credentials thì nó
  restart liên tục, còn chạy bằng credentials của admin thì Cloudflare sẽ chia
  traffic của admin sang máy bạn.
- Web chạy ở `http://localhost:3001` (theo `WEB_PORT`).
- Sửa secret trên Infisical xong thì chạy lại `scripts/dc up -d`. Container chỉ
  đọc biến môi trường lúc được tạo, và compose sẽ tạo lại những container có
  cấu hình đổi.

## 5. Launch từ Canvas vào stack của bạn (không bắt buộc)

Canvas dùng chung đang gửi LTI launch về `app.canxphung.dev`, tức stack của
admin (tool `DA Platform Local`). Luồng LTI và các biến được giải thích ở
[canvas_lti_setup.md](canvas_lti_setup.md). Muốn launch về máy bạn thì làm ba
bước:

1. **Có một URL HTTPS công khai trỏ tới `localhost:3001` trên máy bạn**, ví dụ
   `https://app-<tên>.canxphung.dev`. Nhờ admin tạo hostname trên Cloudflare,
   hoặc tự dùng tunnel của bạn. URL phải cố định, vì Canvas lưu nó trong
   developer key.
2. **Gửi URL cho admin. Admin chạy lệnh sau trên máy có Canvas:**
   ```bash
   docker exec -i \
     -e DA_LTI_TOOL_NAME="DA Platform - <tên>" \
     -e DA_LTI_TOOL_URL=https://<url-của-bạn> \
     -e DA_LTI_JWKS_URL=https://<url-của-bạn>/.well-known/jwks.json \
     canvas-lms-web-1 bundle exec rails runner - < scripts/setup_canvas_lti.rb
   ```
   **Mỗi người phải dùng một `DA_LTI_TOOL_NAME` khác nhau, và khác
   `DA Platform Local`.** Script tìm tool theo tên, trùng tên là ghi đè lên
   tool của người khác. Lệnh in ra một dòng
   JSON có `client_id` và `deployment_id`.
3. **Điền vào `.env` rồi tạo lại web và core-api:**
   ```bash
   LTI_REDIRECT_URI=https://<url-của-bạn>/lti/launch
   LTI_CLIENT_ID=<client_id>
   LTI_DEPLOYMENT_ID=<deployment_id>
   ```
   ```bash
   scripts/dc up -d web core-api
   ```

## 6. Dùng chung DB thì cẩn thận những gì

- **Không chạy `prisma migrate dev`, `prisma migrate reset` hay `prisma db push`
  vào DB chung.** `migrate dev` thấy schema lệch là đề nghị reset cả database.
  Migration được áp bằng `prisma migrate deploy`, và phải báo nhóm trước khi
  chạy.
- **Worker tranh job với nhau.** Hàng đợi BullMQ nằm trên Redis chung, nên
  worker trên máy bạn (`document`, `enrichment`, `outbox`,
  `content-generation`, `answer-grading`) sẽ nhận cả job của người khác và xử
  lý bằng code đang dở của bạn. Nếu không làm phần worker, chỉ bật service bạn
  cần, ví dụ:
  ```bash
  scripts/dc up -d web core-api
  ```
- **Hai tác vụ nền trong `.env.team.example` mặc định bị tắt**
  (`AGS_ENABLED=false`, `CANVAS_AUTO_SYNC_ENABLED=false`). Lý do: core-api của
  mỗi người đều chạy chúng trên cùng DB và cùng Canvas. Chỉ bật khi bạn đang
  làm đúng phần đó.
- **`fedoralap` tắt khi mất điện, và Canvas tắt theo máy admin.** Nếu cả nhóm
  cùng mất kết nối DB hoặc Canvas thì báo admin.

## 7. Lỗi thường gặp

| Triệu chứng | Nguyên nhân / cách sửa |
|---|---|
| `required variable MINIO_ROOT_USER is missing a value` | Bạn gọi `docker compose` trực tiếp. Dùng `scripts/dc`. |
| `infisical: command not found` | Chưa cài CLI (mục 1). |
| Infisical báo chưa đăng nhập, 401, 403 | Chạy lại `infisical login`. Nếu vẫn lỗi thì kiểm tra đã chọn US Region chưa và đã được thêm vào project chưa. |
| core-api hoặc worker timeout khi nối DB, Redis | Tailscale chưa bật, hoặc `fedoralap` đang tắt. Thử `tailscale ping 100.102.89.124`. |
| Container `cloudflared` restart liên tục; xuất hiện thư mục `.cloudflared/credentials.json/` | Quên `--scale cloudflared=0`. Chạy `scripts/dc rm -sf cloudflared` rồi xoá thư mục đó. |
| Lỗi đọc file `/keys/*.pem` | Chưa chạy `node scripts/gen_dev_keys.mjs`. |

---

## Dành cho admin nhóm

**Máy admin chạy `scripts/dc up -d` không kèm `--scale cloudflared=0`.**
Tunnel `app.canxphung.dev` chạy trên máy này; thêm cờ đó vào thì compose sẽ gỡ
container tunnel.

**Thêm thành viên.**

- Infisical: Organization → Members → mời qua email, rồi thêm người đó vào
  project `da-platform`. Gói Free cho tối đa 5 identity, tính cả người lẫn máy.
- Tailscale: mời vào tailnet, hoặc share node `fedoralap`.
- Canvas: tạo tài khoản cho họ.

**Đổi một secret.**

1. Sửa trên web Infisical, rồi báo nhóm chạy `scripts/dc up -d`.
2. Với mật khẩu Postgres, Redis, MinIO, Neo4j, Qdrant: phải đổi cả phía
   `fedoralap` (stack `da-db`; với Postgres là `ALTER ROLE ... PASSWORD`), nếu
   không service sẽ không đăng nhập được.

**Xoá secret bằng CLI.** Cần thêm `--type shared`. Mặc định CLI tìm secret
loại `personal` nên sẽ báo 404:

```bash
infisical secrets delete <TÊN> --env=dev --type shared
```

**Khi một thành viên rời nhóm:**

1. Gỡ họ khỏi Infisical và Tailscale. Gỡ Tailscale là cắt ngay đường vào cả 5
   kho dữ liệu, kể cả khi họ còn nhớ mật khẩu.
2. Rotate những gì họ đã đọc được: `POSTGRES_PASSWORD`, `REDIS_PASSWORD`,
   `MINIO_ROOT_PASSWORD`, `NEO4J_PASSWORD`, `QDRANT_API_KEY`,
   `CANVAS_API_TOKEN` (xoá token cũ trong profile Canvas, tạo token mới).
3. Xoá developer key Canvas của họ (Admin → Developer Keys).
4. Key model là của họ nên không cần làm gì.
