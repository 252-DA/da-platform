# frozen_string_literal: true

require "securerandom"

# Tạo (hoặc dùng lại) user dịch vụ cho core-api trên Canvas và in một token
# không hạn. Chạy lại được: không tạo trùng user, mỗi lần chạy sinh thêm một
# token mới (token cũ vẫn dùng được cho tới khi bị thu hồi).
#
#   docker cp scripts/canvas_service_user.rb canvas-lms-web-1:/tmp/canvas_service_user.rb
#   tok=$(docker exec canvas-lms-web-1 bundle exec rails runner /tmp/canvas_service_user.rb 2>/dev/null \
#         | grep '^DA_TOKEN=' | cut -d= -f2-)
#   infisical secrets set CANVAS_API_TOKEN="$tok" --env=dev --type=shared
#
# Dòng cuối của stdout là `DA_TOKEN=<token>`; không in token ở chỗ nào khác.
# User dịch vụ là Account Admin của root account nhưng KHÔNG phải site admin:
# cờ site_admin_access_token_expiration chỉ giới hạn 1 tuần cho token của
# user đọc được Site Admin (access_token.rb, set_permanent_expiration).

USER_NAME = "DA Platform Service"
LOGIN = "da-service@canvas.local"
TOKEN_PURPOSE = "da-platform core-api"

account = Account.default
site_admin = Account.site_admin

pseudonym = account.pseudonyms.active.by_unique_id(LOGIN).first
user = pseudonym&.user

if user
  warn "Dùng lại user #{user.id} (#{LOGIN})"
else
  user = User.create!(name: USER_NAME)
  user.register!
  password = SecureRandom.hex(24)
  pseudonym = user.pseudonyms.create!(
    account: account,
    unique_id: LOGIN,
    password: password,
    password_confirmation: password
  )
  warn "Đã tạo user #{user.id} (#{LOGIN})"
end

role = Role.get_built_in_role("AccountAdmin", root_account_id: account.resolved_root_account_id)
account_user = account.account_users.active.where(user_id: user.id, role_id: role.id).first
account_user ||= AccountUser.create!(account: account, user: user, role: role)
warn "Account Admin của #{account.name}: account_user #{account_user.id}"

# Phải là admin của root account, không phải site admin.
if site_admin.account_users.active.where(user_id: user.id).exists?
  raise "User #{LOGIN} đang là site admin; token sẽ bị giới hạn 1 tuần. Gỡ quyền site admin rồi chạy lại."
end

token = user.access_tokens.create!(
  developer_key: DeveloperKey.default,
  purpose: TOKEN_PURPOSE
)
if token.permanent_expires_at || token.expires_at
  raise "Token vẫn có hạn (permanent_expires_at=#{token.permanent_expires_at.inspect}, " \
        "expires_at=#{token.expires_at.inspect}); không dùng được cho dịch vụ."
end

puts "DA_TOKEN=#{token.full_token}"
