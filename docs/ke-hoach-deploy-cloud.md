# Kế hoạch deploy da-platform lên cloud

Ngày viết: 2026-11-05. Trạng thái: **kế hoạch, chưa làm bước nào.**

Các con số và nhận xét về code trong tài liệu này được kiểm tra trên nhánh `feat/chatbot-three-modes` ngày 2026-11-05. Chỗ nào chưa kiểm tra được thì có ghi rõ.

---

## 0. Tóm tắt

- **Một VM Linux ở Singapore**, chạy Docker Compose. Toàn bộ app và 5 kho dữ liệu (Postgres 18, Redis, Qdrant, Neo4j, MinIO) đều nằm trên VM này.
- **Image build bằng GitHub Actions**, đẩy lên **GHCR** (`ghcr.io/252-da/da-*`). VM chỉ `pull`, không build. Cả 8 repo `252-DA` đang public nên image cũng để public được, VM không cần đăng nhập registry.
- **Ra Internet qua Cloudflare Tunnel**, giống hiện nay. VM không mở port nào ra ngoài. Bạn quản trị VM qua Tailscale.
- **Canvas vẫn chạy trên Mac** ở giai đoạn này. Muốn LTI launch được thì Mac phải đang bật.
- **Prod tách hẳn dev**: Postgres, Redis và Qdrant của prod là bản riêng. Dev của cả nhóm vẫn dùng DB trên fedoralap như cũ.

Thứ tự làm: GĐ0 chốt quyết định → GĐ1 sửa code cho prod và chạy thử trên Mac → GĐ2 CI build image → GĐ3 dựng VM → GĐ4 chuyển dữ liệu → GĐ5 chuyển `app.canxphung.dev` sang cloud → GĐ6 vận hành (backup, update, rollback) → GĐ7 các việc làm sau.

---

## 1. Quyết định cần chốt trước

Mỗi mục có một khuyến nghị. Nếu đồng ý thì giữ nguyên, nếu không thì sửa trước khi làm GĐ1.

| # | Quyết định | Khuyến nghị | Lý do |
|---|---|---|---|
| D1 | Nhà cung cấp và cấu hình VM | VPS x86 ở Singapore, **4 vCPU / 16 GB RAM / 100 GB SSD**, Ubuntu 24.04. Tối thiểu chấp nhận được: 8 GB RAM + 4 GB swap. | Cách tính ở mục 3. x86 khớp runner mặc định của GitHub Actions. Đặt ở Singapore để gần edge SIN của Cloudflare. |
| D2 | Ai giữ `app.canxphung.dev` | **Prod giữ.** Stack dev trên Mac chuyển sang một hostname mới và một LTI tool mới, giống cách làm cho thiện và bình. | Tool "DA Platform" hiện có (client_id `10000000000001`) cùng các placement trong khóa học vẫn chạy được mà không phải sửa gì trong Canvas. Tên hostname và tên tool cho Mac do bạn đặt. |
| D3 | Dữ liệu ban đầu của prod | **Copy từ fedoralap** (mục GĐ4). | Câu hỏi, LO mapping và enrichment đều đã tốn tiền LLM để sinh ra. Bắt đầu trống thì phải sinh lại và index lại bằng Voyage. |
| D4 | Lưu file (object storage) | **Dùng MinIO trên VM trước**, chuyển sang R2 ở GĐ7. | Code hiện tại chạy được với MinIO mà không phải sửa. Đổi sang R2 cần sửa code storage, mà phần đó nên chờ bình push code B2 (đã ghi trong memory/plan R2). |
| D5 | Key LLM cho prod | **Key riêng cho prod, có đặt hạn mức chi tiêu, và không dùng Gemini free tier.** | Gemini 3-flash bản free chỉ cho 20 request/ngày. Prod mà dùng key đó thì chỉ sau vài lượt sinh quiz là hết quota cho cả ngày. Tài khoản của ai thì bạn quyết. |
| D6 | Compose hay k3s | **Compose trên 1 VM.** | Chỉ có một máy thì k3s chỉ làm tốn thêm RAM và thêm một lớp manifest phải viết. Image build ra dùng lại được nguyên cho k3s nếu sau này chuyển. |
| D7 | Secret của prod | **File `.env.prod` trên VM (chmod 600).** Bản gốc giữ trong Infisical, env `prod`. Khi có thay đổi thì bạn tự export ra file. | Gói free của Infisical giới hạn 5 identity, mà nhóm đã dùng gần hết. Làm cách này thì VM không cần machine identity. |

---

## 2. Kiến trúc đích

```
                    HTTPS
Trình duyệt ───────────────► Cloudflare edge ──tunnel──► VM Singapore (Docker Compose)
(GV, SV, iframe Canvas)                                  ├─ cloudflared
                                                         ├─ web (Next standalone, :3000)
                                                         ├─ core-api (:4000 HTTP, :50051 gRPC)
                                                         ├─ ai-tutor, mcp-service, embedding-service
                                                         ├─ 6 worker (cùng 1 image, khác command)
                                                         └─ postgres:18, redis, qdrant, neo4j, minio
                                                            (chỉ trong mạng nội bộ compose)

Canvas trên Mac (canvas.canxphung.dev) ◄── JWKS, REST API, AGS ── web, core-api trên VM
Voyage, Gemini, DeepSeek              ◄── HTTPS ra ngoài ──────── worker, ai-tutor, embedding-service
Bạn ──── Tailscale SSH ────► VM
GitHub Actions ── push ──► ghcr.io/252-da/da-* ◄── pull ── VM
```

Không service nào publish port ra host. Chỉ có cloudflared đi ra ngoài, và Tailscale dùng cho quản trị.

---

## 3. Cần bao nhiêu RAM

Số đo bằng `docker stats` trên Mac ngày 2026-11-05. Đây là **dev mode, lúc đang rảnh**:

| Service | Đo được | Ghi chú cho prod |
|---|---|---|
| web | 1,49 GB | Đây là dev server của Next. Bản standalone thường chỉ vài trăm MB, nhưng chưa đo. |
| core-api | 615 MB | Đang chạy `nest --watch`. Bản prod chạy `node dist/main` sẽ nhẹ hơn, chưa đo. |
| enrichment / content-gen / answer-grading / outbox worker | 215–229 MB mỗi cái | |
| micro-content-video-worker | 414 MB | Tăng lên khi ffmpeg render. |
| document-worker | 192 MB lúc rảnh, **đỉnh 2,5 GB** khi Docling chạy OCR | Đỉnh 2,5 GB là số đo ngày 2026-10-28. |
| embedding-service | 56 MB | Backend Voyage nên không nạp model vào RAM. |
| mcp-service / ai-tutor / cloudflared | 92 / 117 / 37 MB | |
| Postgres, Redis, Qdrant, Neo4j, MinIO | **chưa đo** (đang chạy trên fedoralap) | Ước tính 2–3 GB. Neo4j phải giới hạn heap, xem GĐ1. |

Tổng cộng: app lúc rảnh khoảng 3,5–4 GB, Docling vọt thêm 2,3 GB, DB thêm 2–3 GB, **đỉnh khoảng 8–9,5 GB**. Vì vậy 8 GB là sát nút, 16 GB thì thoải mái và còn chỗ nếu sau này đưa Canvas lên (GĐ7). Dung lượng ổ đĩa: image khoảng 8–10 GB, cộng dữ liệu, cộng log và backup tạm, nên 100 GB là đủ.

**Chọn nhà cung cấp (D1).** Giá thay đổi liên tục, lúc mua nhớ xem lại:
- **Hetzner Cloud, location Singapore**: rẻ nhất nếu tính theo GB RAM. Có điều traffic đi kèm ở Singapore ít hơn nhiều so với châu Âu (một nguồn bên thứ ba ghi 1 TB/tháng). Nên tìm loại x86 (shared AMD).
- **Azure for Students**: được 100 USD credit, không cần thẻ. Với một VM 16 GB, số credit này chỉ đủ vài tháng, nên tính trước xem phải dùng tới ngày bảo vệ hay không.
- Không khuyến nghị **Oracle Always Free**. Nhiều nguồn nói hạn mức ARM đã giảm còn 2 OCPU / 12 GB trong năm 2026. Ngoài ra nó thường xuyên báo hết máy trống, và còn có chính sách thu hồi instance để rảnh. Image cũng phải build cho arm64.

---

## 4. Code hiện tại còn thiếu gì để chạy prod

| # | Chỗ | Vấn đề | Cách sửa (làm ở GĐ1) |
|---|---|---|---|
| G1 | [worker/Dockerfile](../worker/Dockerfile) | ENTRYPOINT là `uv run --frozen python -m`. Vì `pyproject.toml` khai báo `default-groups = ["dev"]`, mỗi lần container khởi động là uv lại cài nhóm dev (log outbox-worker có dòng "Installed 13 packages"). Ở prod như vậy là khởi động chậm, phải có mạng mới chạy được, và pytest bị đưa lên prod. | Trong prod compose, đổi entrypoint thành `["python", "-m"]` vì `PATH` đã chứa `.venv/bin`. Không dùng `dev_reload`. |
| G2 | [core-api/Dockerfile](../core-api/Dockerfile) | Stage `prod` không chứa Prisma CLI (đó là devDependency, đã bị `pnpm prune --prod` xóa) và cũng không có thư mục `prisma/`. Nghĩa là image prod không chạy được `migrate deploy`. | Thêm stage `migrate` (`FROM base`, `CMD npx prisma migrate deploy`), build thành image riêng `da-core-api-migrate`. |
| G3 | [core-api/Dockerfile](../core-api/Dockerfile) | Chỉ copy `package.json` rồi chạy `pnpm install --no-frozen-lockfile`. Hai lần build có thể ra hai bộ phiên bản khác nhau. | Copy thêm `pnpm-lock.yaml` và dùng `--frozen-lockfile`. |
| G4 | 6 worker | Cả 6 build từ cùng `worker/Dockerfile` với cùng context. Hiện mỗi worker build ra một image riêng, mỗi cái khoảng 2,9 GB. | Build **một** image `da-worker`, mỗi service chỉ khác `command`. |
| G5 | document-worker | Docling tải model về cache lúc chạy lần đầu (chưa kiểm tra chính xác thư mục nào). Vì container chạy bằng root nên khả năng cao là `/root/.cache`. | Mount volume `worker_cache:/root/.cache`. Đặt `mem_limit: 3g` và giữ `WORKER_CONCURRENCY=1`. |
| G6 | ai-tutor | Trong compose dev, service này chạy uvicorn với `--reload`. | Prod dùng CMD mặc định của image (đã không có `--reload`). |
| G7 | [docker-compose.yml](../docker-compose.yml) | Đây là file cho dev: bind mount source, publish khoảng 20 port, mật khẩu mặc định. | Viết file mới `deploy/docker-compose.prod.yml`, không kế thừa file dev. |
| G8 | Trang thư viện media ([media-library-client.tsx:257](../web/src/app/manage/media/media-library-client.tsx#L257)) | Trình duyệt `PUT` thẳng lên presigned URL của storage. MinIO trên VM nằm trong mạng nội bộ nên luồng này không chạy, y như trên dev bây giờ. Riêng viewer tài liệu thì vẫn chạy được vì web proxy ở phía server. | Để nguyên ở GĐ1–6. Xử lý ở GĐ7 khi chuyển sang R2 và cấu hình CORS. |
| G9 | [deploy/README.md](../deploy/README.md) | Nội dung là hướng dẫn self-host trên Fedora từ thời đầu, đã lỗi thời. | Viết lại theo tài liệu này sau khi deploy xong. |
| G10 | Code chưa có trên GitHub | Nhánh `feat/chatbot-three-modes` của meta-repo và 6 submodule chưa push. `core-api`, `web`, `worker` mỗi repo còn 3 file chưa commit. CI chỉ build được những gì đã có trên GitHub. | GĐ0: chốt commit nào sẽ lên prod, rồi commit và push (bạn tự làm hoặc bảo mình làm). |

Những chỗ không phải sửa: stage `runner` của `web` với `output: "standalone"`, stage `prod` của `core-api` (ngoài G2–G3), Dockerfile của `mcp-service` và `embedding-service`. `.dockerignore` đã loại `.env` và `web/keys`. `core-api/keys` chỉ có public key. Cho nên image không chứa secret và để public được.

---

## 5. Các giai đoạn

### GĐ0 — Chuẩn bị (phần của bạn)

1. Chốt D1–D7.
2. Mua hoặc tạo VM theo D1, thêm SSH public key của Mac vào.
3. Chốt commit sẽ lên prod (G10): merge vào `master` hoặc dùng nhánh riêng, sau đó push meta-repo cùng các submodule.
4. Tạo key LLM cho prod theo D5 và đặt hạn mức chi tiêu.
5. Kiểm tra Canvas API token. Token site-admin bị giới hạn 1 tuần, token gần nhất hết hạn ngày 2026-10-29. Prod cần một token còn hạn, đồng thời phải có cách gia hạn (xem rủi ro 2 ở mục 7).
6. Infisical: tạo env `prod` rồi điền danh sách biến ở GĐ3 bước 8. Mật khẩu DB tạo mới, dạng hex 32 ký tự để nhúng vào URL không bị lỗi.

Xong khi: SSH được vào VM, commit cần deploy đã có trên GitHub.

### GĐ1 — Sửa code cho prod, chạy thử trên Mac

Mình làm được phần này. Mọi thay đổi đều để ở trạng thái chưa commit cho bạn xem.

1. **core-api/Dockerfile**: sửa G2 và G3.
   ```dockerfile
   COPY core-api/package.json core-api/pnpm-lock.yaml ./
   RUN pnpm install --frozen-lockfile --ignore-scripts
   # ...
   FROM base AS migrate
   CMD ["npx", "prisma", "migrate", "deploy"]
   ```
2. **deploy/docker-compose.prod.yml**, file mới, gồm:
   - Tất cả image đều có dạng `ghcr.io/252-da/da-<tên>:${IMAGE_TAG:?}`.
   - Không service nào có `ports:`. Không bind mount source. Chỉ mount `keys/` (read-only) và các volume dữ liệu.
   - Worker dùng chung một khối cấu hình:
     ```yaml
     x-worker: &worker
       image: ghcr.io/252-da/da-worker:${IMAGE_TAG:?}
       entrypoint: ["python", "-m"]
       restart: unless-stopped
       volumes: [worker_cache:/root/.cache]

     services:
       document-worker:
         <<: *worker
         command: ["worker.runners.document_worker"]
         mem_limit: 3g
         environment: { <<: *worker-env, WORKER_TYPE: document, WORKER_CONCURRENCY: "1", ... }
     ```
   - `migrate` dùng image `da-core-api-migrate`, đặt trong `profiles: ["ops"]` để chỉ chạy khi gọi `docker compose run --rm migrate`.
   - Biến môi trường: `APP__ENV=production`. `NODE_ENV=production` cho web và core-api. `AGS_ENABLED=true`, `CANVAS_AUTO_SYNC_ENABLED=true` (vì prod là nơi duy nhất bật hai cái này). `LTI_COOKIE_SECURE=true`. Bỏ `CI: "true"` và `WATCHPACK_POLLING`.
   - Cấu hình kho dữ liệu:
     - Postgres `postgres:18-alpine`, volume mount ở `/var/lib/postgresql` (giống dev).
     - Redis chạy `--requirepass ... --appendonly yes --maxmemory-policy noeviction`. BullMQ không được để mất key.
     - Qdrant đặt `QDRANT__SERVICE__API_KEY`.
     - Neo4j đặt `NEO4J_server_memory_heap_max__size=512m` và `NEO4J_server_memory_pagecache_size=256m`.
     - MinIO dùng mật khẩu thật.
     - **Phiên bản Qdrant và Neo4j phải giống trên fedoralap** (`/home/canxphung/da-db`) thì snapshot/dump ở GĐ4 mới nạp vào được.
   - `cloudflared` chạy bằng `TUNNEL_TOKEN` (tunnel quản lý trên dashboard), không dùng `credentials.json`.
3. **deploy/deploy.sh**: nhận `<sha>`, lần lượt chạy backup → `compose pull` → `run --rm migrate` → `up -d` → `image prune` (giữ lại 2 tag gần nhất).
4. **deploy/backup.sh**: dump Postgres và đẩy lên R2 (xem GĐ6).
5. **Chạy thử trên Mac**: build các image prod bằng `docker buildx build --target ...` (ra arm64, chỉ để thử, không push), rồi `docker compose -f deploy/docker-compose.prod.yml up` với `.env.prod` dùng giá trị test và DB trống. Sau đó chạy `migrate` để kiểm tra Prisma 7 trong stage mới đọc được `prisma.config.ts`.

Xong khi: stack prod lên đủ trên Mac, mọi container ở trạng thái `healthy`, `migrate` chạy hết 18 migration trên DB trống, mở được trang `/` của web.

### GĐ2 — CI build và push lên GHCR

Workflow mới `.github/workflows/images.yaml` trong meta-repo:

```yaml
name: images
on:
  push:
    branches: [master]
  workflow_dispatch:
permissions:
  contents: read
  packages: write
jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        include:
          - { name: web,               file: web/Dockerfile,               target: runner }
          - { name: core-api,          file: core-api/Dockerfile,          target: prod }
          - { name: core-api-migrate,  file: core-api/Dockerfile,          target: migrate }
          - { name: worker,            file: worker/Dockerfile,            target: "" }
          - { name: embedding-service, file: embedding-service/Dockerfile, target: "" }
          - { name: mcp-service,       file: mcp-service/Dockerfile,       target: "" }
          - { name: ai-tutor,          file: ai-tutor/Dockerfile,          target: "" }
    steps:
      - uses: actions/checkout@v4
        with: { submodules: true }
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v6
        with:
          context: .
          file: ${{ matrix.file }}
          target: ${{ matrix.target }}
          platforms: linux/amd64
          push: true
          tags: |
            ghcr.io/252-da/da-${{ matrix.name }}:${{ github.sha }}
            ghcr.io/252-da/da-${{ matrix.name }}:master
          cache-from: type=gha,scope=${{ matrix.name }}
          cache-to: type=gha,mode=max,scope=${{ matrix.name }}
```

Một số lưu ý:
- Tag theo SHA của meta-repo. SHA này đã cố định commit của mọi submodule, nên một tag ứng với đúng một bộ code.
- Image worker nặng khoảng 3 GB. Nếu runner báo hết ổ đĩa, thêm một bước dọn đĩa (xóa toolchain không dùng trên runner) trước bước build.
- Lần push đầu tiên tạo package ở chế độ private. Vào **Org 252-DA → Packages → từng package → Package settings → Change visibility → Public**. Nếu org chặn package public thì phải bật ở Org settings → Packages. Cũng có thể để private, khi đó VM phải `docker login ghcr.io` bằng PAT chỉ có quyền `read:packages`.
- Dùng `workflow_dispatch` để build từ nhánh khác `master` khi cần cho lần deploy đầu.

Xong khi: `docker pull ghcr.io/252-da/da-worker:<sha>` chạy được từ một máy chưa đăng nhập registry.

### GĐ3 — Dựng VM

Mỗi bước có lệnh kiểm tra đi kèm.

1. **Cập nhật hệ thống và tạo user**: `apt update && apt upgrade`, tạo user `deploy` thuộc nhóm `sudo`, cài `unattended-upgrades`.
2. **Swap 4 GB**: `fallocate -l 4G /swapfile`, `mkswap`, `swapon`, rồi thêm vào `/etc/fstab`. Kiểm tra bằng `free -h`.
3. **Tailscale**: `tailscale up --ssh`. Kiểm tra bằng `ssh deploy@<tên-tailscale>` từ Mac.
4. **Đóng cửa**:
   - Tắt đăng nhập SSH bằng mật khẩu.
   - Bật firewall của nhà cung cấp: chặn mọi inbound. SSH công khai cũng chặn, sau khi đã SSH được qua Tailscale.
   - UFW: `default deny incoming`, `allow in on tailscale0`.
   - **Chú ý: port do Docker publish sẽ đi vòng qua UFW.** Đó là lý do prod compose không có `ports:` nào.
5. **Docker Engine và compose plugin**: cài từ apt repo của docker.com. Tạo `/etc/docker/daemon.json` với `{"log-driver":"json-file","log-opts":{"max-size":"10m","max-file":"3"}}` để log không làm đầy ổ.
6. **Thư mục deploy**: `git clone https://github.com/252-DA/da-platform.git /opt/da-platform`. Không cần `--recurse-submodules`, vì VM chỉ dùng thư mục `deploy/`.
7. **Key**: copy `lti.pem`, `lti.pub.pem`, `bff-to-core.pem` (từ `web/keys`) và `bff-to-core.pub.pem` (từ `core-api/keys`) sang `/opt/da-platform/keys/` bằng `scp` qua Tailscale, rồi `chmod 600`. **Phải đúng cặp key đang dùng**, vì Canvas đã có public key của tool qua JWKS.
8. **`/opt/da-platform/.env.prod`** (chmod 600), export từ Infisical env `prod`. Các nhóm biến:
   - Kho dữ liệu: `POSTGRES_USER/PASSWORD/DB`, `REDIS_PASSWORD`, `QDRANT_API_KEY`, `NEO4J_PASSWORD`, `MINIO_ROOT_USER/PASSWORD`.
   - Canvas: `CANVAS_PUBLIC_URL`, `CANVAS_API_URL`, `CANVAS_API_TOKEN`.
   - LTI: `LTI_LMS_TYPE`, `LTI_PLATFORM_URL`, `LTI_ISSUER_URL`, `LTI_AUTH_URL`, `LTI_JWKS_URL`, `LTI_TOKEN_URL`, `LTI_CLIENT_ID`, `LTI_DEPLOYMENT_ID`, `LTI_KEY_ID`, `LTI_REDIRECT_URI`, `LTI_EXTRA_CLIENT_IDS`, `LTI_EXTRA_DEPLOYMENT_IDS`, `LTI_COOKIE_SAMESITE`, `LTI_COOKIE_SECURE`. Giá trị lấy đúng như `.env` hiện tại, vì prod sẽ nhận lại `app.canxphung.dev` (D2).
   - Embedding: `EMBEDDING_BACKEND`, `EMBEDDING_API_BASE_URL`, `EMBEDDING_API_KEY`, `EMBEDDING_API_MODEL`, `EMBEDDING_API_DIMENSIONS`. Phải giống dev, nếu không vector sẽ khác không gian với dữ liệu copy sang.
   - LLM: `GEMINI_API_KEY`, `DEEPSEEK_API_KEY`, các `LLM_PROFILE__*` (nếu có).
   - Còn lại: `TUNNEL_TOKEN`, `IMAGE_TAG`.
9. **Tạo tunnel `da-prod`** trên Cloudflare Zero Trust (Networks → Tunnels) và lấy token. **Chưa gắn `app.canxphung.dev`**, việc đó để GĐ5.

Xong khi: `docker compose -f deploy/docker-compose.prod.yml --env-file .env.prod config` không báo lỗi, và Mac SSH vào VM được qua Tailscale.

### GĐ4 — Dựng kho dữ liệu và chuyển dữ liệu từ fedoralap

Mình không SSH được vào fedoralap, nên các lệnh chạy trên fedoralap là phần của bạn. Thêm VM vào tailnet để VM nhìn thấy fedoralap.

1. Trên VM: `docker compose ... up -d postgres redis qdrant neo4j minio`.
2. **Postgres**:
   ```bash
   # fedoralap
   docker exec <pg-container> pg_dump -U app -d app -Fc > app.dump
   scp app.dump deploy@<vm>:/opt/da-platform/
   # VM
   docker compose ... exec -T postgres pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner < app.dump
   docker compose ... run --rm migrate      # áp các migration mới hơn bản trên fedoralap
   ```
3. **Qdrant**: tạo snapshot collection `documents` trên fedoralap (`POST /collections/documents/snapshots`), tải file về, rồi upload vào prod (`POST /collections/documents/snapshots/upload?priority=snapshot`). Sau đó so số điểm ở hai bên (`GET /collections/documents`).
4. **Neo4j** (bản community chỉ dump được khi DB đang tắt): dừng container neo4j trên fedoralap → chạy `neo4j-admin database dump neo4j --to-path=/backups` trong một container tạm gắn cùng volume → copy file → `neo4j-admin database load` trên VM.
5. **MinIO**: từ VM, dùng container `pgsty/mc` chạy `mc mirror fedoralap/documents prod/documents`. Kiểm tra lại số object ở hai bên.

Lưu ý: bản copy là ảnh chụp tại một thời điểm. Từ lúc này dữ liệu dev và prod tách nhau. Muốn bản prod đầy đủ thì báo nhóm ngừng ghi vào DB dev trong lúc dump.

Xong khi: số dòng của các bảng chính, số điểm trong Qdrant và số object trong MinIO khớp với fedoralap.

### GĐ5 — Lên app và chuyển `app.canxphung.dev` sang cloud

1. `deploy/deploy.sh <sha>` để lên toàn bộ app. Đợi đến khi `docker compose ps` báo mọi service `healthy`.
2. **Kiểm tra trước khi chuyển**:
   - Gắn tạm một hostname phụ vào tunnel `da-prod` (bạn đặt tên). Mở trang chủ web bằng điện thoại dùng 4G.
   - Từ trong VM: `docker compose exec core-api wget -qO- http://localhost:4000/...` (health), và kiểm tra các port health của worker (8081–8086) trong mạng nội bộ.
   - Hostname phụ này **không launch LTI được**, vì redirect URI của tool đang trỏ tới `app.canxphung.dev`.
3. **Chuyển hostname** (sẽ gián đoạn vài phút):
   1. Trên Mac, dừng service `cloudflared` của da-platform.
   2. Trong Cloudflare DNS, xóa CNAME `app` đang trỏ tới tunnel cũ `74779ab4…`.
   3. Thêm public hostname `app.canxphung.dev → http://web:3000` vào tunnel `da-prod`.
4. **Chuyển stack dev trên Mac** (theo D2):
   - Tạo tunnel và hostname mới cho Mac theo cách trong `docs/dev-setup.md`, mục "Dành cho admin nhóm".
   - Chạy `scripts/setup_canvas_lti.rb` với một `DA_LTI_TOOL_NAME` mới (bạn đặt tên). Script upsert theo tên, nên **không được dùng lại tên "DA Platform"**.
   - Trong `.env` trên Mac, cập nhật `LTI_*` mới và đặt `AGS_ENABLED=false`, `CANVAS_AUTO_SYNC_ENABLED=false`.
   - Sửa [deploy/cloudflared.da-platform.yml](../deploy/cloudflared.da-platform.yml) theo hostname mới.
5. Chạy hết checklist smoke test ở mục 6.

Xong khi: checklist mục 6 qua hết.

**Nếu hỏng giữa chừng**: gắn lại CNAME `app` về tunnel cũ và bật lại cloudflared trên Mac. Mọi thứ trở về như trước, vì dev vẫn dùng DB fedoralap.

### GĐ6 — Vận hành

- **Cập nhật phiên bản**: merge vào `master` → CI build xong → trên VM chạy `deploy/deploy.sh <sha>`. Script luôn dump Postgres trước khi migrate.
- **Rollback**: chạy `deploy/deploy.sh <sha-cũ>`. Migration Prisma chỉ đi một chiều, nên nếu migration làm hỏng dữ liệu thì phải restore từ bản dump vừa tạo trước đó rồi mới lùi image.
- **Backup** (cron trên VM, đẩy lên một bucket R2 riêng cho backup; gói free của R2 có 10 GB):
  - Hằng ngày: `pg_dump -Fc`, giữ 14 bản.
  - Hằng tuần: snapshot Qdrant và `mc mirror` MinIO. Có thể index lại Qdrant từ Postgres, nhưng sẽ tốn tiền Voyage.
  - Neo4j: dump hằng tuần (mất vài phút downtime). Hoặc bỏ qua nếu kiểm tra được rằng outbox-worker dựng lại được graph từ Postgres. Điều này chưa kiểm tra.
  - **Restore thử một lần** vào một DB tạm. Backup chưa từng restore thử thì chưa tính là có backup.
- **Giám sát tối thiểu**: tạo health check miễn phí (UptimeRobot hoặc Cloudflare Health Checks) gọi vào `app.canxphung.dev`. Khi cần thì xem `docker stats` và `docker compose logs`. Bộ Grafana/Loki/Prometheus có sẵn trong `deploy/` để GĐ7.
- **Ổ đĩa**: `deploy.sh` đã prune image cũ. Nên kiểm tra `df -h` mỗi tuần.

### GĐ7 — Làm sau, khi prod đã chạy ổn

1. **Chuyển sang R2**:
   - Tổng quát hóa client storage trong `core-api/src/document/document-storage.service.ts` và `packages-ai/.../minio_adapter.py`: endpoint https, `region: "auto"`.
   - Cấu hình CORS cho trang media (G8).
   - Copy dữ liệu từ MinIO sang R2 bằng `rclone`.
   - Việc này chờ bình push code B2 trước.
2. **Đưa Canvas lên cloud** để demo không phụ thuộc Mac. Canvas chạy production mode cần thêm khoảng 4 GB RAM và khá nhiều công dựng. Nên tính riêng, kể cả khả năng dùng một VM thứ hai.
3. **Deploy tự động**: thêm một job cuối workflow, dùng `tailscale/github-action` để SSH vào VM và chạy `deploy.sh`.
4. **Observability**: `deploy/docker-compose.observability.yml`, kèm Cloudflare Access để chặn người lạ vào Grafana.
5. Làm image `embedding-service` nhẹ hơn (hiện 1,8 GB vì vẫn cài torch dù đang dùng backend Voyage).

---

## 6. Checklist smoke test sau khi chuyển

- [ ] Mở `https://app.canxphung.dev` bằng điện thoại 4G.
- [ ] Từ một khóa học trong Canvas, mở **DA Platform** bằng tài khoản giáo viên rồi bằng tài khoản sinh viên. Launch phải thành công, session phải giữ được trong iframe.
- [ ] Mở **Trợ giảng AI** (registration phụ trong `LTI_EXTRA_CLIENT_IDS`).
- [ ] Upload một tài liệu. document-worker parse xong, số điểm trong Qdrant tăng lên.
- [ ] Mở viewer tài liệu: PDF hiện ra (đi qua route proxy của web).
- [ ] Sinh quiz cho một LO. Job chạy hết ở content-generation-worker.
- [ ] Chatbot ở cả ba chế độ (vector, tools, graph). Bấm vào trích dẫn thì mở đúng trang.
- [ ] Sinh viên làm bài có câu tự luận ngắn. answer-grading-worker chấm xong, AGS đẩy điểm lên sổ điểm Canvas.
- [ ] Log core-api có dòng đồng bộ Canvas tự động chạy.
- [ ] Trang `/manage/models` đổi được model.
- [ ] `sudo reboot` VM. Sau khi khởi động lại, mọi service tự lên mà không cần làm gì.

---

## 7. Rủi ro

| # | Rủi ro | Cách giảm |
|---|---|---|
| 1 | Canvas vẫn ở trên Mac. Mac tắt hoặc ngủ thì không ai launch được. | Giữ Mac bật trong những buổi demo. Tính GĐ7 mục 2 trước ngày bảo vệ. |
| 2 | Token Canvas API của site-admin chỉ sống 1 tuần (do flag ẩn). Token hết hạn thì đồng bộ và AGS lỗi mà không ai thấy. | Đặt lịch gia hạn, hoặc tìm cách gỡ giới hạn đó trong Canvas local. Nên theo dõi lỗi 401 trong log core-api. |
| 3 | Key LLM hết quota hoặc vượt chi phí. | Áp dụng D5: key riêng, có hạn mức chi tiêu. |
| 4 | Docling dùng nhiều RAM, có thể bị OOM. | `mem_limit: 3g` cho document-worker, concurrency 1. Prod không có `dev_reload` nên khi worker chết, `restart: unless-stopped` sẽ tự khởi động lại. |
| 5 | GHCR hiện "đang miễn phí" và GitHub hứa sẽ báo trước nếu tính phí. | Theo dõi thông báo của GitHub. Image dùng tag theo SHA nên muốn chuyển registry khác thì chỉ phải đổi prefix. |
| 6 | Runner của GitHub hết ổ đĩa khi build worker. | Thêm bước dọn đĩa trên runner (GĐ2). |
| 7 | Độ trễ qua Cloudflare từ VN: khoảng nửa số request đi vòng qua edge FRA/MRS (đo ngày 2026-10-17). | Đưa server lên cloud không sửa được chuyện này. Nằm ngoài phạm vi kế hoạch. |
| 8 | Dữ liệu prod và dev lệch nhau sau GĐ4. | Nói rõ với nhóm: dev chỉ để phát triển, dữ liệu dùng để demo nằm ở prod. |
| 9 | Docker publish port vượt qua UFW. | Prod compose không có `ports:`. Firewall của nhà cung cấp chặn mọi inbound. |

---

## 8. Ai làm gì

**Mình (Claude) làm được ngay khi bạn đồng ý với D1–D7:**
- Các thay đổi Dockerfile ở G1–G3.
- `deploy/docker-compose.prod.yml`, `deploy/deploy.sh`, `deploy/backup.sh`.
- Workflow `.github/workflows/images.yaml`.
- Chạy thử stack prod trên Mac (GĐ1 bước 5).
- Viết lại `deploy/README.md` sau khi deploy xong.

Mình không commit hay push nếu bạn chưa cho phép.

**Phần của bạn** (cần tài khoản, dashboard hoặc máy mà mình không vào được):
- Mua VM.
- Cấu hình trên Cloudflare: tunnel, DNS, hostname.
- Tạo env `prod` trên Infisical.
- Key LLM và token Canvas.
- Đổi visibility của package trên GHCR.
- Các lệnh dump trên fedoralap.
- Đặt tên hostname và tên LTI tool cho stack dev trên Mac.
- Commit và push code sẽ deploy.
