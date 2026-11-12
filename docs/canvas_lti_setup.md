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
| Scope | AGS: `lineitem`, `result.readonly`, `score`<br>Asset Processor: `noticehandlers`, `asset.readonly`, `report`<br>NRPS: `contextmembership.readonly` (đọc danh sách lớp, xem [mục dưới](#custom-field-và-danh-sách-lớp-nrps)) |
| Custom field | `canvas_course_id`, `canvas_user_id`, `canvas_module_id`, `canvas_module_item_id`, `canvas_assignment_id` và sáu trường `assignment_*` (bảng [dưới](#custom-field-và-danh-sách-lớp-nrps)). Tool chat `DA Trợ giảng AI` chỉ có `canvas_course_id` và `canvas_user_id` |
| Privacy | `public`: Canvas gửi tên và email người dùng |

Tool riêng của thành viên (tạo ngày 08/10/2026). Menu của các tool này có thêm
tên người, ví dụ **DA Platform (thien)**:

| Tool | `client_id` | `deployment_id` | URL |
|---|---|---|---|
| `DA Platform - thien` | `10000000000003` | `2:8865aa05…` | `https://app-thien.canxphung.dev` |
| `DA Platform - binh` | `10000000000004` | `3:8865aa05…` | `https://app-binh.canxphung.dev` |

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

## Custom field và danh sách lớp (NRPS)

Bước 1 của [ke-hoach-tich-hop-canvas.md](ke-hoach-tich-hop-canvas.md): DA biết cả
lớp, không chỉ người đã bấm vào DA.

### Custom field

Tool khai các custom field sau trong `scripts/setup_canvas_lti.rb`. Canvas mở
rộng biến thành giá trị thật ở mỗi launch và gửi trong claim
`https://purl.imsglobal.org/spec/lti/claim/custom`; web chuyển nguyên claim này
cho core-api (`customClaims`).

| Custom field | Biến Canvas | Có giá trị khi | DA dùng để |
|---|---|---|---|
| `canvas_course_id` | `$Canvas.course.id` | mọi launch trong khóa học | lưu `lms_course_ref.lms_platform_course_id`; suy ra địa chỉ NRPS |
| `canvas_user_id` | `$Canvas.user.id` | mọi launch | lưu `lms_user_mappings.lms_platform_user_id` |
| `canvas_module_id` | `$Canvas.module.id` | launch từ một module item | Deep Linking lấy module từ đây trước, rồi mới giải mã `?data=JWT` |
| `canvas_module_item_id` | `$Canvas.moduleItem.id` | launch từ một module item | chưa dùng |
| `canvas_assignment_id` | `$Canvas.assignment.id` | launch từ một Assignment | chưa dùng (Bước 2) |
| `assignment_points` | `$Canvas.assignment.pointsPossible` | launch từ một Assignment | chưa dùng (Bước 2) |
| `assignment_due`, `assignment_unlock`, `assignment_lock` | `$Canvas.assignment.dueAt.iso8601`, `unlockAt.iso8601`, `lockAt.iso8601` | Assignment có ngày tương ứng | chưa dùng (Bước 2) |
| `assignment_attempts` | `$Canvas.assignment.allowedAttempts` | launch từ một Assignment | chưa dùng (Bước 2) |
| `assignment_published` | `$Canvas.assignment.published` | launch từ một Assignment | chưa dùng (Bước 2) |

Biến không có ngữ cảnh không bị bỏ khỏi claim: Canvas để nguyên chuỗi, ví dụ
`"$Canvas.module.id"`. Nên phía nhận chỉ chấp nhận `canvas_user_id` và
`canvas_course_id` khi là số nguyên dương, và Deep Linking chỉ dùng
`canvas_module_id` khi là số. Launch Deep Linking từ menu ⋮ của module
(`module_menu_modal`) không gắn với module item nên `canvas_module_id` ở đó luôn
chưa mở rộng; module vẫn lấy từ `?data=JWT` như trước.

Claim chỉ có trong launch **sau khi** chạy lại script đăng ký. Launch cũ không có
`canvas_*`, và DA vẫn chạy bình thường nhờ các đường dự phòng bên dưới.

### Đọc danh sách lớp bằng NRPS

Scope `https://purl.imsglobal.org/spec/lti-nrps/scope/contextmembership.readonly`
nằm trong `scopes` của tool chính (không cần cho tool chat). Sau khi có scope,
launch mang thêm claim
`https://purl.imsglobal.org/spec/lti-nrps/claim/namesroleservice` với
`context_memberships_url`; web chuyển nó cho core-api, nơi lưu vào
`lms_course_ref.nrps_context_memberships_url`.

Chưa có claim (chưa launch lại sau khi đăng ký) thì core-api tự suy ra
`<LTI_PLATFORM_URL>/api/lti/courses/<id khóa Canvas>/names_and_roles`, với id lấy
từ `lms_platform_course_id` hoặc, nếu trống, từ
`GET /api/v1/courses/lti_context_id:<context>`, rồi lưu lại.

NRPS gọi bằng tên miền **công khai** của Canvas, không đổi sang
`canvas.docker:3000` như `CANVAS_API_URL`. Canvas kiểm tra `aud` của token theo
host của request, mà token được xin ở tên miền công khai, nên gọi qua địa chỉ
nội bộ trả `401 the 'aud' is invalid`. core-api dùng lại token LTI của AGS (khác
scope, cache riêng) và từ chối gửi token tới host khác `LTI_PLATFORM_URL`.

Đồng bộ danh sách lớp (`RosterSyncService`) chạy khi:

- giảng viên, trợ giảng hoặc admin mở DA từ Canvas (cooldown 2 phút, khóa Redis
  riêng với đồng bộ tài liệu);
- vòng quét 15 phút (`CANVAS_AUTO_SYNC_ENABLED`), mỗi khóa một job;
- bấm **Đồng bộ từ Canvas** ở trang tài liệu.

Kết quả ghi vào `canvas_sync_runs` với `kind = 'roster'` và hiện thành dòng
"Danh sách lớp: n sinh viên · đồng bộ lúc …" (hoặc lỗi màu đỏ) ngay cạnh nút
đồng bộ.

Map role theo **URI chính xác**, TA xét trước giảng viên vì Canvas gửi TA kèm cả
`membership#Instructor`:

| URI role của NRPS | Role trong khóa |
|---|---|
| `membership/Instructor#TeachingAssistant` | `ta` |
| `membership#Instructor`, `membership#ContentDeveloper` | `instructor` |
| `membership#Mentor` | `observer` |
| `membership#Learner`, `membership#Member` | `learner` |
| khác | bỏ qua, đếm vào `skipped` |

Ghi vào DB:

- `lms_user_mappings`: tạo dòng cho người chưa từng mở DA (`lms_sub` = `user_id`
  của NRPS, chính là `sub` của id_token). Role nền tảng của dòng mới là
  `instructor` cho giảng viên/TA, `learner` cho còn lại; dòng đã có không bị đổi
  role. Tên chỉ cập nhật khi Canvas gửi tên thật.
- `course_memberships.source`: `launch` (người đó đã mở DA) hoặc `nrps`;
  `status`: `active` hoặc `inactive`. Người không còn trong danh sách Canvas
  chuyển sang `inactive`, **không bị xóa** (lịch sử làm bài còn nguyên). Danh sách
  Canvas trả về rỗng thì bỏ qua bước này.
- Một lần launch đặt lại `source = 'launch'`, `status = 'active'`.

Trang kết quả quiz và bảng nắm vững LO của learning agent lấy mẫu số từ sinh
viên `learner` đang `active` của khóa. Phiên đăng nhập và `listCourses` chưa xét
`status` (Canvas đã chặn người rời lớp ở bước launch).

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
- có rồi thì cập nhật URL, placement, scope và custom field, giữ nguyên
  `client_id` và `deployment_id`. Scope và placement đã có từ nơi khác được giữ
  lại; custom field khai trong script thắng khi trùng tên.

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

Tool chat `DA Trợ giảng AI` đăng ký riêng bằng
[scripts/setup_canvas_chat_lti.rb](../scripts/setup_canvas_chat_lti.rb), cùng cách:

```bash
docker exec -i \
  -e DA_LTI_TOOL_URL=https://app.canxphung.dev \
  -e DA_LTI_JWKS_URL=https://app.canxphung.dev/.well-known/jwks.json \
  canvas-lms-web-1 bundle exec rails runner - < scripts/setup_canvas_chat_lti.rb
```

Script in ra một dòng JSON gồm `action` (`created`/`updated`), `client_id` và
`deployment_id`; điền hai giá trị sau vào `.env`. Xong thì tải lại trang
Modules để Canvas lấy menu mới. Việc này không cần build lại hay restart
Canvas.

**Tool riêng cho thành viên:** chạy cùng lệnh với `DA_LTI_TOOL_NAME` khác
`DA Platform Local`, kèm URL của người đó. Tên `DA Platform - <tên>` cho menu
`DA Platform (<tên>)`; muốn hậu tố khác thì đặt `DA_LTI_MENU_SUFFIX`. Các bước
đầy đủ nằm ở
[dev-setup.md, mục 5](dev-setup.md#5-launch-từ-canvas-vào-stack-của-bạn-không-bắt-buộc).
Tool của thành viên đã đăng ký trước Bước 1 chưa có custom field và scope NRPS
cho tới khi chạy lại script với tên của họ.

## Canvas do trường host (Instructure)

Không chạy được script vì không có `rails runner`. Admin của trường phải tạo
Developer Key loại LTI bằng tay với cùng các giá trị như trên: target link URI,
OIDC initiation URL, redirect URI, public JWK URL, ba scope AGS, ba scope
Asset Processor (`noticehandlers`, `asset.readonly`, `report`), scope NRPS
`contextmembership.readonly`, các custom field ở mục
[Custom field](#custom-field) và ba placement
(Course Navigation; Module Menu Modal với Deep Linking; Document Processor
`ActivityAssetProcessor` với Deep Linking, xem
[essay-asset-processor.md](essay-asset-processor.md)). Sau đó bật
key, cài app bằng Client ID ở cấp account, rồi lấy Deployment ID. Tên menu có
thể khác theo phiên bản Canvas. Biến môi trường điền theo
[.env.canvas.example](../.env.canvas.example): issuer vẫn là
`https://canvas.instructure.com`, còn auth và JWKS nằm ở `sso.canvaslms.com`.

## Token REST API của Canvas

LTI 1.3 không có service đọc file, nên việc đồng bộ tài liệu trong Modules và
file đề cương phải dùng REST API với `CANVAS_API_TOKEN` (Infisical, shared).
Token thuộc về một user dịch vụ riêng trên Canvas, không thuộc admin.

### Cấp token mới (cách dùng chính)

1. Chạy `scripts/canvas_service_user.rb` trong container Canvas và đưa token
   thẳng lên Infisical, không để token hiện ra màn hình hay lịch sử lệnh:

   ```bash
   docker cp scripts/canvas_service_user.rb canvas-lms-web-1:/tmp/canvas_service_user.rb
   tok=$(docker exec canvas-lms-web-1 bundle exec rails runner /tmp/canvas_service_user.rb 2>/dev/null \
         | grep '^DA_TOKEN=' | cut -d= -f2-)
   [ -n "$tok" ] && infisical secrets set CANVAS_API_TOKEN="$tok" --env=dev --type=shared
   unset tok
   ```

   Script tìm hoặc tạo user **DA Platform Service** (đăng nhập
   `da-service@canvas.local`), cấp **Account Admin** ở root account, không cấp
   site admin, rồi tạo một access token không hạn (`purpose` = `da-platform
   core-api`). Chạy lại không tạo user trùng; mỗi lần chạy sinh thêm một token
   mới, token cũ vẫn dùng được cho tới khi thu hồi. Nếu token sinh ra vẫn có
   hạn, script báo lỗi và không in token.
2. Báo nhóm chạy `scripts/dc up -d --no-deps core-api`. Container chỉ đọc biến
   môi trường lúc được tạo, nên `docker restart` không đủ.
3. Kiểm tra: mở trang **Tài liệu khóa học** (`/manage/documents`), không có dòng
   đỏ "Token Canvas lỗi". core-api cũng tự kiểm tra token mỗi 24 giờ và khi
   khởi động bằng `GET /api/v1/users/self`; kết quả nằm ở khóa Redis
   `canvas:token-status` và hiện cạnh nút **Đồng bộ từ Canvas**.

Thu hồi token cũ sau khi đổi (liệt kê rồi `destroy` token không còn dùng):

```bash
docker exec canvas-lms-web-1 bundle exec rails runner \
  'Pseudonym.active.by_unique_id("da-service@canvas.local").first.user.access_tokens.each { |t| puts [t.id, t.created_at, t.purpose].inspect }'
```

### Vì sao không dùng token của `admin@canvas.local`

`admin@canvas.local` là site admin, và Canvas mặc định bật cờ ẩn
`site_admin_access_token_expiration`: mọi token của user đọc được Site Admin bị
ép hạn tối đa 1 tuần, bất kể ô Expires (`AccessToken#set_permanent_expiration`).
Token đầu tiên vì thế hết hạn ngày 2026-10-04, và từ đó cứ mỗi tuần mọi lệnh
gọi REST lại nhận `401 Expired access token`. Cờ chỉ chạm token của site admin
nên user dịch vụ (admin root account, không thuộc Site Admin) không bị ảnh
hưởng và không cần tắt cờ.

Cờ không có nút trên giao diện. Nếu buộc phải dùng token của site admin (ví dụ
Canvas khác không tạo được user dịch vụ), tắt cờ trước khi tạo token ở **Account
→ Settings → New Access Token** (để trống ô **Expires**):

```bash
docker exec canvas-lms-web-1 bundle exec rails runner \
  'Account.site_admin.disable_feature!(:site_admin_access_token_expiration)'
```

### Địa chỉ Canvas cho core-api

Mặc định `CANVAS_API_URL` lấy theo `CANVAS_PUBLIC_URL`, nên mọi request của
core-api đi vòng qua tunnel Cloudflare dù Canvas chạy cùng máy. Máy chạy cả
Canvas lẫn DA đặt `CANVAS_API_URL=http://canvas.docker:3000` trong `.env`
(`canvas.docker` được compose ánh xạ tới máy host qua `extra_hosts`); xem
[canvas-document-auto-sync.md](canvas-document-auto-sync.md#internal-canvas-api-url).
Các máy khác giữ nguyên địa chỉ tunnel.

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
