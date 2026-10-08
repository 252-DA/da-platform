# Kết nối DA với Canvas qua LTI 1.3

DA là một **LTI 1.3 tool**, còn Canvas là **platform**. Canvas của nhóm tự host
trên máy admin, tại `https://canvas.canxphung.dev`. Tài liệu này gồm: tool đang
được đăng ký thế nào, các biến môi trường, luồng launch, cách đăng ký lại và
cách xử lý lỗi. Cách chạy stack dev nằm ở [dev-setup.md](dev-setup.md).

## Hiện trạng (kiểm tra ngày 08/10/2026)

| | |
|---|---|
| Tên tool trên Canvas | `DA Platform Local` |
| `client_id` | `10000000000001` |
| `deployment_id` | `1:8865aa05b4b79b64a91a86042e43af5ea8ae79eb`, ở root account, bật cho mọi khóa học |
| URL của tool | `https://app.canxphung.dev`: OIDC `/lti/login`, redirect `/lti/launch`, JWKS `/.well-known/jwks.json` |
| Placement | `course_navigation`: mục **DA Platform** trong menu khóa học (`LtiResourceLinkRequest`, mở `/`)<br>`module_menu_modal`: **Sinh quiz bằng DA** trong menu ⋮ của module (`LtiDeepLinkingRequest`, mở `/lti/deep-link`, xem [canvas-module-quiz.md](canvas-module-quiz.md)) |
| Scope AGS | `lineitem`, `result.readonly`, `score` |
| Privacy | `public`: Canvas gửi tên và email người dùng |

## Hai chiều ký

| Chiều | Ai ký | Bằng khóa nào | Bên kia kiểm bằng |
|---|---|---|---|
| Canvas → DA | Canvas ký `id_token` khi launch | Khóa của Canvas | web tải `LTI_JWKS_URL` (JWKS của Canvas) |
| DA → Canvas | web ký response deep linking; core-api ký client assertion để lấy token AGS | `web/keys/lti.pem`, `kid` = `LTI_KEY_ID` | Canvas tải `public_jwk_url` đã đăng ký, tức `https://<tool>/.well-known/jwks.json` |

Vì Canvas lấy public key qua URL, đổi cặp khóa `lti.pem` thì không phải đăng ký
lại tool. Chỉ cần URL JWKS vẫn trỏ đúng web đang chạy.

## Luồng launch

1. Canvas gọi `/lti/login` (OIDC initiation) với `iss`, `login_hint`,
   `target_link_uri`. web kiểm `iss` = `LTI_ISSUER_URL`, lưu `state` và `nonce`
   vào Redis 5 phút (dùng một lần), rồi chuyển hướng tới `LTI_AUTH_URL`.
2. Canvas POST `id_token` về `LTI_REDIRECT_URI` (`/lti/launch`).
3. web kiểm tra:
   - chữ ký, đối chiếu JWKS của Canvas;
   - hạn token;
   - `aud` có chứa `LTI_CLIENT_ID`;
   - `deployment_id` = `LTI_DEPLOYMENT_ID` (bỏ qua nếu để trống);
   - `state` và `nonce`.
4. Map vai trò LTI, theo thứ tự ưu tiên:

   | Vai trò LTI | Vai trò trong DA |
   |---|---|
   | `Administrator` | administrator |
   | `Instructor`, `Faculty`, `Staff` | giảng viên |
   | `TeachingAssistant` | TA |
   | `Observer`, `Mentor` | observer |
   | `Learner`, `Student`, `Member` | sinh viên |

   Vai trò khác bị từ chối với 403 `Unsupported LTI role`. Sau đó web gọi
   core-api `launchSync` để tạo hoặc cập nhật người dùng, khóa học và ghi danh.
5. Đặt cookie `sid` rồi chuyển vào app. DA chạy trong iframe của Canvas (khác
   domain), nên cookie phải là `SameSite=None; Secure`. web thêm `Partitioned`
   (CHIPS) để trình duyệt chặn cookie bên thứ ba vẫn giữ được phiên.

## Biến môi trường

| Biến | Giá trị hiện tại | Nằm ở | Ý nghĩa |
|---|---|---|---|
| `LTI_LMS_TYPE` | `canvas` | Infisical | Chọn giá trị mặc định cho Canvas |
| `LTI_PLATFORM_URL` | `https://canvas.canxphung.dev` | Infisical | URL gốc của Canvas |
| `LTI_ISSUER_URL` | `https://canvas.instructure.com` | Infisical | Phải khớp `lti_iss` trong `config/security.yml` của Canvas. Canvas tự host vẫn dùng giá trị này theo mặc định |
| `LTI_AUTH_URL` | `https://canvas.canxphung.dev/api/lti/authorize_redirect` | Infisical | Endpoint OIDC auth |
| `LTI_JWKS_URL` | `https://canvas.canxphung.dev/api/lti/security/jwks` | Infisical | JWKS của Canvas |
| `LTI_TOKEN_URL` | `https://canvas.canxphung.dev/login/oauth2/token` | Infisical | Lấy token AGS |
| `LTI_COOKIE_SAMESITE`, `LTI_COOKIE_SECURE` | `none`, `true` | Infisical | Bắt buộc khi chạy trong iframe HTTPS |
| `LTI_CLIENT_ID` | `10000000000001` | `.env` | `client_id` của tool |
| `LTI_DEPLOYMENT_ID` | `1:8865aa05…` | `.env` | Deployment của tool |
| `LTI_REDIRECT_URI` | `https://app.canxphung.dev/lti/launch` | `.env` | Phải nằm trong `redirect_uris` đã đăng ký |
| `LTI_KEY_ID` | `ai-nextjs-1` | `.env` | `kid` trong JWKS của tool |
| `AGS_ENABLED` | trống | `.env` | Trống = bật khi đã có client id và khóa; `false` = tắt gửi điểm |
| `CANVAS_PUBLIC_URL`, `CANVAS_API_TOKEN` | | Infisical | REST API của Canvas, dùng để đồng bộ tài liệu và đề cương, không thuộc LTI. Xem mục [Token REST API](#token-rest-api-của-canvas) |

Biến trên Infisical là chung cho cả nhóm, vì cả nhóm dùng chung một Canvas.
Biến trong `.env` gắn với từng tool, tức stack của từng người.

Nếu `LTI_LMS_TYPE=canvas` và để trống `LTI_AUTH_URL`/`LTI_JWKS_URL`, web dùng
`sso.canvaslms.com`, giá trị dành cho Canvas của Instructure. Với Canvas tự host
thì phải đặt hai biến này.

## Đăng ký hoặc cập nhật tool (Canvas tự host)

[scripts/setup_canvas_lti.rb](../scripts/setup_canvas_lti.rb) chạy trong
container Canvas. Script tìm tool theo **tên**:

- chưa có tool tên đó thì tạo mới;
- có rồi thì cập nhật URL, placement và scope, giữ nguyên `client_id` và
  `deployment_id`.

Vì vậy chạy lại nhiều lần vẫn an toàn.

| Biến | Mặc định | |
|---|---|---|
| `DA_LTI_TOOL_NAME` | `DA Platform Local` | Tên tool, cũng là khóa để tìm |
| `DA_LTI_TOOL_URL` | `http://localhost:3001` | URL công khai của web |
| `DA_LTI_JWKS_URL` | `http://host.docker.internal:3001/.well-known/jwks.json` | URL Canvas dùng để lấy public key của tool |

Cập nhật tool chính (admin chạy trên máy có Canvas):

```bash
docker exec -i \
  -e DA_LTI_TOOL_URL=https://app.canxphung.dev \
  -e DA_LTI_JWKS_URL=https://app.canxphung.dev/.well-known/jwks.json \
  canvas-lms-web-1 bundle exec rails runner - < scripts/setup_canvas_lti.rb
```

**Luôn truyền `DA_LTI_TOOL_URL`.** Nếu thiếu, script ghi đè URL của
`DA Platform Local` thành `http://localhost:3001` và mọi launch qua Canvas sẽ
hỏng.

Script in ra một dòng JSON gồm `action` (`created`/`updated`), `client_id` và
`deployment_id`; điền hai giá trị sau vào `.env`. Xong thì tải lại trang
Modules để Canvas lấy menu mới. Việc này không cần build lại hay restart
Canvas.

**Tool riêng cho thành viên:** chạy cùng lệnh với `DA_LTI_TOOL_NAME` khác
`DA Platform Local`, kèm URL của người đó. Các bước đầy đủ nằm ở
[dev-setup.md, mục 5](dev-setup.md#5-launch-từ-canvas-vào-stack-của-bạn-không-bắt-buộc).

## Canvas do trường host (Instructure)

Không chạy được script vì không có `rails runner`. Admin của trường phải tạo
Developer Key loại LTI bằng tay với cùng các giá trị như trên: target link URI,
OIDC initiation URL, redirect URI, public JWK URL, ba scope AGS và hai
placement (Course Navigation; Module Menu Modal với Deep Linking). Sau đó bật
key, cài app bằng Client ID ở cấp account, rồi lấy Deployment ID. Tên menu có
thể khác theo phiên bản Canvas. Biến môi trường điền theo
[.env.canvas.example](../.env.canvas.example): issuer vẫn là
`https://canvas.instructure.com`, còn auth và JWKS nằm ở `sso.canvaslms.com`.

## Token REST API của Canvas

LTI 1.3 không có service đọc file, nên việc đồng bộ tài liệu trong Modules và
file đề cương phải dùng REST API với `CANVAS_API_TOKEN`. Môi trường dev dùng
token của admin. Các bước đổi token:

1. Đăng nhập Canvas bằng tài khoản admin, vào **Account → Settings → New Access
   Token**.
2. Cập nhật `CANVAS_API_TOKEN` trên Infisical.
3. Báo nhóm chạy `scripts/dc up -d core-api`.

Lịch đồng bộ được mô tả ở
[canvas-document-auto-sync.md](canvas-document-auto-sync.md).

## Kiểm tra nhanh

```bash
# JWKS của tool: phải có kid ai-nextjs-1, RS256
curl -s https://app.canxphung.dev/.well-known/jwks.json

# JWKS của Canvas
curl -s https://canvas.canxphung.dev/api/lti/security/jwks

# Các tool đang đăng ký trên Canvas (chỉ đọc, mất khoảng nửa phút để Rails khởi động)
docker exec canvas-lms-web-1 bundle exec rails runner '
Lti::Registration.active.each do |r|
  c = (r.internal_lti_configuration || {}).with_indifferent_access
  puts({ name: r.name, client_id: r.developer_key&.global_id.to_s,
         redirect_uris: c[:redirect_uris], jwk_url: c[:public_jwk_url],
         deployments: r.deployments.active.map(&:deployment_id) }.to_json)
end'
```

Test tự động cho claim, chữ ký và response deep linking: chạy `pnpm test:lti`
trong `web/`.

## Lỗi thường gặp

| Triệu chứng | Nguyên nhân / cách sửa |
|---|---|
| `502` ở `canvas.canxphung.dev` | Canvas trên máy admin đang tắt, cổng `:3000` không trả lời. Tunnel vẫn chạy bình thường. Kiểm tra `docker ps -a \| grep canvas-lms`. |
| `Unknown LTI issuer` (400) | `LTI_ISSUER_URL` khác `iss` mà Canvas gửi. Đối chiếu `lti_iss` trong `config/security.yml` của Canvas. |
| `Invalid or expired OIDC state` (403) | Quá 5 phút giữa login và launch, Redis bị restart, hoặc trang launch bị gửi lại. Mở lại tool từ Canvas. |
| `Unexpected LTI audience` | `LTI_CLIENT_ID` không khớp `client_id` của tool đã launch. |
| `Invalid LTI deployment_id` | `LTI_DEPLOYMENT_ID` sai. Lấy lại từ output của script. |
| `Failed to fetch platform JWKS` | web không gọi được `LTI_JWKS_URL`, thường vì Canvas tắt. |
| Canvas báo lỗi redirect URI, không quay về `/lti/launch` | URL trong đăng ký khác `LTI_REDIRECT_URI`, hay gặp nhất khi script bị chạy thiếu `DA_LTI_TOOL_URL`. Chạy lại script với URL đúng. |
| Mở tool thấy trang trắng hoặc bị đăng xuất liên tục trong iframe | Cookie bị chặn. Kiểm tra `LTI_COOKIE_SAMESITE=none`, `LTI_COOKIE_SECURE=true`, và tool phải chạy HTTPS. Thử nghiệm qua HTTP thì đặt `lax`/`false` và cấu hình Canvas mở tool ở tab mới. |
| Lỗi RSA key yếu khi kiểm chữ ký | JWKS của Canvas dev còn hai khóa mẫu rất ngắn (512 bit). web chỉ chấp nhận chúng khi `NODE_ENV` khác `production` (compose đang đặt `development`) hoặc khi `LTI_ALLOW_WEAK_RSA_VERIFICATION=true`. |
| Điểm không về sổ điểm Canvas | Bài tập chưa publish thì Canvas trả 422 và DA chờ, không phải lỗi. Ngoài ra kiểm tra `AGS_ENABLED`, scope AGS của tool, và đúng một stack đang chạy poller AGS. Chi tiết ở [canvas-module-quiz.md](canvas-module-quiz.md). |
