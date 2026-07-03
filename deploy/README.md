# Deploy — Môi trường chung (self-host Fedora + Cloudflare Tunnel)

> Mục tiêu: 1 PC ở nhà (Fedora, 16GB) chạy toàn bộ stack = vừa là DB chung, vừa là staging/demo/pilot, phơi ra `*.canxphung.dev` qua HTTPS.
> Mô hình: dev local từng service → push → deploy về con PC này. Migration schema do chủ `core-api` đẩy để team không phá DB của nhau.

**Vì sao kiểu này:** PC ở nhà nằm sau NAT/IP động → Cloudflare Tunnel mở kết nối *ra ngoài*, không cần mở port router / IP tĩnh, và Cloudflare cấp SSL free ở edge. `canxphung.dev` bị ép HTTPS toàn thời gian (`.dev` trong HSTS preload) nên bắt buộc có SSL — tunnel lo việc đó.

---

## Lộ trình 5 chặng

| Chặng | Làm gì | Xong là |
|---|---|---|
| 0 | Đưa code lên được PC | clone được repo trên PC server |
| 1 | Cài Docker trên Fedora | `docker compose version` chạy |
| 2 | Dựng stack hiện có | `docker compose ps` xanh hết |
| 3 | Cloudflare Tunnel | `https://app.canxphung.dev` mở được |
| 4 | Grafana/Loki/Prometheus | có dashboard |
| 5 | Sống sót reboot + uptime pilot | bật lại PC vẫn tự lên |

Nhắm hết **chặng 3** trong buổi đầu (mốc "có HTTPS public"). Chặng 4–5 làm sau.

---

## Chặng 0 — Đưa code lên PC

Để `clone` trên con Fedora, repo phải nằm trên org `252-DA`. `packages-ai` + `report` đã có remote; **`core-api`, `web`, `worker` chưa có remote → push lên org trước.**

```bash
git clone git@github.com:252-DA/core-api.git
git clone git@github.com:252-DA/web.git
git clone git@github.com:252-DA/core-chunking.git   # = packages-ai
git clone git@github.com:252-DA/worker.git
# + copy docker-compose.yml và .env sang PC
```

> Đây là lý do phải "fix git" trước: không push thì không deploy được.

---

## Chặng 1 — Docker trên Fedora

Fedora mặc định Podman; cài **Docker CE** cho khớp `docker-compose`:

```bash
# Fedora cũ (dnf4):
sudo dnf -y install dnf-plugins-core
sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo

# Fedora 41+ (dnf5) thì dòng addrepo là:
# sudo dnf config-manager addrepo --from-repofile=https://download.docker.com/linux/fedora/docker-ce.repo

sudo dnf install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker $USER     # logout/login lại để khỏi sudo
```

✅ Verify: `docker compose version` + `docker run --rm hello-world`.

> **Gotcha Fedora #1 — SELinux:** bind-mount file config vào container sẽ bị "permission denied". Thêm `:z` (hoặc `:Z`) vào volume, vd `./prometheus.yml:/etc/prometheus/prometheus.yml:z`. DB dùng named volume thì không dính — nhớ cho chặng 4.
> **Gotcha #2 — firewalld:** nếu container không gọi được nhau, kiểm tra firewalld đang chặn bridge network của docker.

---

## Chặng 2 — Dựng stack hiện có

```bash
cd <thư mục có docker-compose.yml>
cp .env.canvas.example .env      # rồi điền GEMINI_API_KEY, mật khẩu DB...
docker compose up -d
docker compose ps                # xem service nào published port nào
```

✅ Verify: tất cả `healthy`. **Ghi lại port từng service** (cột PORTS) — chặng 3 cần. Đặc biệt `web` và `core-api`.

> **STT:** đặt `STT_PROVIDER=api` (Google/OpenAI) — KHÔNG chạy Whisper local trên PC này, ngốn CPU/GPU.

---

## Chặng 3 — Cloudflare Tunnel

**Khái niệm:** `cloudflared` mở kết nối ra Cloudflare. Request tới `app.canxphung.dev` → edge Cloudflare (SSL ở đây) → chui qua hầm về PC → tới container. Không mở port router, không cần IP tĩnh. (Mô hình "zero-trust egress tunnel".)

Điều kiện: `canxphung.dev` đang dùng nameserver Cloudflare (add site vào Cloudflare nếu chưa).

```bash
# cài cloudflared (rpm trực tiếp):
sudo dnf install -y "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-x86_64.rpm"

cloudflared tunnel login            # mở browser, chọn zone canxphung.dev
cloudflared tunnel create da-stack  # in ra UUID + đường dẫn file .json credentials
```

Tạo `~/.cloudflared/config.yml` (thay UUID + user + đúng port từ chặng 2):

```yaml
tunnel: <UUID-vừa-tạo>
credentials-file: /home/<user>/.cloudflared/<UUID>.json
ingress:
  - hostname: app.canxphung.dev      # web
    service: http://localhost:3000
  - hostname: api.canxphung.dev      # core-api
    service: http://localhost:8000
  # chặng 4 thêm:
  # - hostname: grafana.canxphung.dev
  #   service: http://localhost:3001
  - service: http_status:404         # bắt buộc có dòng catch-all cuối
```

Trỏ DNS (cloudflared tự tạo CNAME):

```bash
cloudflared tunnel route dns da-stack app.canxphung.dev
cloudflared tunnel route dns da-stack api.canxphung.dev
```

Chạy thử foreground:

```bash
cloudflared tunnel run da-stack
```

✅ Verify: mở `https://app.canxphung.dev` từ điện thoại (4G, khác wifi) → thấy web, SSL xanh.

---

## Chặng 4 — Observability (Grafana + Loki + Prometheus + Alloy)

> Nguyên tắc: dựng **bản tối thiểu** ở Sprint 1, giá trị thật từ pilot (Sprint 4) khi nó đẻ số liệu cho C5/C6 (latency, cost token, throughput). Đừng gold-plate dashboard tuần này.

Các file đã có sẵn trong `deploy/`:
- `docker-compose.observability.yml` — Prometheus + Loki + Grafana + Alloy, merge chung network `default`.
- `prometheus.yml` — scrape metrics `grpc-server:9090`, `*-worker:9091/9092/9093` (đã `METRICS__ENABLED=true`). `http-api` và `core-api` để comment, bật sau khi verify endpoint.
- `loki-config.yml` — Loki single-binary, lưu filesystem, giữ log 7 ngày.
- `alloy-config.alloy` — Grafana Alloy gom log mọi container qua `docker.sock` → đẩy Loki (không phá `docker logs`).
- `grafana/provisioning/datasources/datasources.yml` — auto nối Prometheus + Loki, khỏi cấu hình tay.

**Chạy** (từ repo root, merge 2 compose):
```bash
# đặt mật khẩu Grafana trong .env: GRAFANA_PASSWORD=<gì đó mạnh>
docker compose -f docker-compose.yml -f deploy/docker-compose.observability.yml up -d
```

✅ Verify:
- `http://localhost:3001` → Grafana (login admin / `GRAFANA_PASSWORD`).
- Prometheus → Status → Targets: `chunking-grpc` + `workers` phải `UP`.
- Grafana → Explore → datasource Loki → thấy log container.

**Gotcha Fedora:**
- Bind-mount config đều có `:z` (SELinux) — đừng bỏ.
- Alloy đọc `docker.sock` hay bị SELinux chặn → đã set `security_opt: [label=disable]` cho riêng nó.

**Phơi ra HTTPS (nối chặng 3):** thêm vào `~/.cloudflared/config.yml`:
```yaml
  - hostname: grafana.canxphung.dev
    service: http://localhost:3001
```
rồi `cloudflared tunnel route dns da-stack grafana.canxphung.dev`.

> **Bảo mật:** Grafana phơi public thì PHẢI đổi mật khẩu admin (không để `admin/admin`), và nên bật **Cloudflare Access** (email allowlist) cho `grafana.canxphung.dev` để chỉ team vào được.

---

## Chặng 5 — Sống sót reboot + uptime cho pilot

```bash
# cloudflared thành systemd service (sống qua reboot):
sudo cp ~/.cloudflared/config.yml /etc/cloudflared/config.yml
sudo cloudflared service install
sudo systemctl enable --now cloudflared
```

- Docker compose: đảm bảo `restart: unless-stopped` cho mọi service.
- Tắt sleep/suspend của PC (PC phải bật 24/7).
- Docker tự lên sau boot: `sudo systemctl enable docker` (đã làm ở chặng 1).

> **Cảnh báo uptime pilot:** PC nhà phải bật 24/7 + mạng ổn định suốt ≥4 tuần pilot. Mất điện / net chập chờn = SV không vào được, mất data. Dev/demo bây giờ PC nhà OK; tới cửa pilot (Sprint 4) nếu thấy chập chờn thì thuê 1 VPS rẻ riêng cho 4 tuần pilot.

---

## Tham chiếu

- Kế hoạch GĐ2: [docs/kehoach_gd2.md](../docs/kehoach_gd2.md)
- Stack/infra hiện có: [docker-compose.yml](../docker-compose.yml)
