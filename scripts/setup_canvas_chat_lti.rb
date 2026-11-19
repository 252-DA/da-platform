# frozen_string_literal: true

require "uri"

# Đăng ký phụ "Trợ giảng AI": một mục riêng ở menu trái của khóa học, mở trang chat
# đầy đủ. Canvas chỉ cho mỗi đăng ký một course_navigation và đăng ký chính đã dùng
# cho "DA Platform", nên mục này cần đăng ký riêng (client_id/deployment riêng)
# cùng trỏ về app và cùng khóa JWKS. Web nhận nó qua LTI_EXTRA_CLIENT_IDS và
# LTI_EXTRA_DEPLOYMENT_IDS (in ra ở cuối).
#
# Chạy trong container Rails của Canvas, nhớ truyền URL thật của tool:
#   docker exec -i -e DA_LTI_TOOL_URL=https://app.canxphung.dev \
#     -e DA_LTI_JWKS_URL=https://app.canxphung.dev/.well-known/jwks.json \
#     canvas-lms-web-1 bundle exec rails runner - < scripts/setup_canvas_chat_lti.rb

tool_name = ENV.fetch("DA_LTI_CHAT_TOOL_NAME", "DA Trợ giảng AI")
tool_base_url = ENV.fetch("DA_LTI_TOOL_URL", "http://localhost:3001").sub(%r{/+$}, "")
tool_domain = URI.parse(tool_base_url).host
tool_jwks_url = ENV.fetch("DA_LTI_JWKS_URL", "http://host.docker.internal:3001/.well-known/jwks.json")

account = Account.default
admin = account.active_account_users.preload(:user).filter_map(&:user).first
admin ||= User.active.first
raise "No active Canvas administrator/user found" unless admin

registration_params = {
  name: tool_name,
  admin_nickname: tool_name,
  description: "Trợ giảng AI trả lời dựa trên tài liệu khóa học",
  vendor: "252-DA",
  lock_deploying: true,
  workflow_state: "on"
}

configuration_params = {
  title: tool_name,
  description: "Trợ giảng AI trả lời dựa trên tài liệu khóa học",
  target_link_uri: "#{tool_base_url}/",
  oidc_initiation_url: "#{tool_base_url}/lti/login",
  redirect_uris: ["#{tool_base_url}/lti/launch"],
  public_jwk_url: tool_jwks_url,
  scopes: [],
  domain: tool_domain,
  tool_id: "da-platform-chat",
  privacy_level: "public",
  # Id Canvas của khóa học và người dùng, để core-api gắn với khóa/người của DA.
  custom_fields: {
    canvas_course_id: "$Canvas.course.id",
    canvas_user_id: "$Canvas.user.id"
  },
  launch_settings: {
    text: "Trợ giảng AI",
    icon_url: "#{tool_base_url}/icons/tro-giang-ai.svg"
  },
  placements: [
    {
      placement: "course_navigation",
      enabled: true,
      message_type: "LtiResourceLinkRequest",
      text: "Trợ giảng AI",
      icon_url: "#{tool_base_url}/icons/tro-giang-ai.svg",
      target_link_uri: "#{tool_base_url}/",
      custom_fields: { target_kind: "chat", chat_layout: "page" }
    }
  ]
}.with_indifferent_access

registration = Lti::Registration.active.find_by(account: account, name: tool_name)
action = registration ? "updated" : "created"
registration =
  if registration
    Lti::UpdateRegistrationService.call(
      id: registration.id,
      account: account,
      updated_by: admin,
      registration_params: registration_params,
      configuration_params: configuration_params,
      comment: "Synced by da-platform/scripts/setup_canvas_chat_lti.rb"
    )
  else
    Lti::CreateRegistrationService.call(
      account: account,
      created_by: admin,
      registration_params: registration_params,
      configuration_params: configuration_params
    )
  end

deployment = registration.deployments.active.find_by(context: account)
deployment ||= registration.new_external_tool(account, current_user: admin, available: true, enabled: true)
deployment.update!(workflow_state: registration.privacy_level) if deployment.workflow_state == "disabled"

control = Lti::ContextControl.active.find_by(deployment: deployment, account: account, course_id: nil)
control&.update!(available: true, updated_by: admin)

puts({
  action: action,
  registration_id: registration.id,
  tool_id: deployment.id,
  LTI_EXTRA_CLIENT_IDS: deployment.global_developer_key_id.to_s,
  LTI_EXTRA_DEPLOYMENT_IDS: deployment.deployment_id,
  available: control&.available
}.to_json)
