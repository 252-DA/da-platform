# frozen_string_literal: true

# Tạo (hoặc dùng lại) user học sinh test trên Canvas dev.
# Chạy lại được: nếu login đã tồn tại thì chỉ in thông tin, không tạo trùng.

USER_NAME = "Học Sinh Test"
LOGIN = "student@canvas.local"
PASSWORD = "Student@123"

account = Account.default

pseudonym = account.pseudonyms.active.by_unique_id(LOGIN).first
user = pseudonym&.user

if user
  warn "Dùng lại user #{user.id} (#{LOGIN}) — không đổi mật khẩu"
else
  user = User.create!(name: USER_NAME)
  user.register!
  user.pseudonyms.create!(
    account: account,
    unique_id: LOGIN,
    password: PASSWORD,
    password_confirmation: PASSWORD
  )
  warn "Đã tạo user #{user.id} (#{USER_NAME} <#{LOGIN}>)"
end

puts "USER_ID=#{user.id}"
puts "LOGIN=#{LOGIN}"
