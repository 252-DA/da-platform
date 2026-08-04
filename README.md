# da-platform — Hệ thống LMS tự động tạo Micro-Content & Quiz bằng Generative AI

Meta-repo của đồ án. Code từng service nằm trong **git submodule**:

| Thư mục | Repo | Nhánh chính | Vai trò |
|---|---|---|---|
| `core-api/` | 252-DA/core-api | `master` | NestJS — auth, LTI 1.3, quiz, review, curriculum |
| `web/` | 252-DA/web | `main` | Next.js — UI instructor/learner |
| `worker/` | 252-DA/worker | `master` | Python — document/enrichment/outbox workers |
| `packages-ai/` | 252-DA/core-chunking | `dev` | Python — pipeline parse/chunk/embed/index |
| `ai-sdk/` | 252-DA/ai-sdk | `master` | Python — model runtime và MCP client dùng chung |
| `ai-tutor/` | 252-DA/ai-tutor | `master` | FastAPI — trợ giảng AI bám theo nội dung khóa học |
| `report/` | 252-DA/report | `master` | LaTeX — báo cáo LVTN (bản chính: `lvtn_en/`) |

Root repo chỉ giữ **glue**: `docker-compose*.yml`, `deploy/`, `scripts/`, env examples.

## Clone lần đầu

```bash
git clone --recurse-submodules git@github.com:252-DA/da-platform.git DA
```

Lỡ clone thường rồi thì: `git submodule update --init --recursive`

## 3 quy tắc SỐNG CÒN khi làm việc với submodule

1. **Vào submodule là phải đứng trên nhánh** (mặc định sau clone là detached HEAD):
   ```bash
   cd worker && git switch master   # rồi mới code
   ```
2. **Commit 2 bước, đúng thứ tự** — xong việc trong submodule:
   ```bash
   cd worker && git add -A && git commit -m "..." && git push   # bước 1: push repo con TRƯỚC
   cd .. && git add worker && git commit -m "bump worker" && git push   # bước 2: cập nhật pointer ở root
   ```
   Push root mà chưa push repo con → teammate clone về **vỡ ngay** (`reference is not a tree`).
3. **Pull ở root không tự kéo submodule:**
   ```bash
   git pull && git submodule update --init --recursive
   ```
   Hoặc set một lần cho khỏe: `git config submodule.recurse true`

## Chạy hệ thống

```bash
cp .env.canvas.example .env   # điền secrets
docker compose up -d --build
```

Setup LTI với Canvas: xem `docs/canvas_lti_setup.md`.
