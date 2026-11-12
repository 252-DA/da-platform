# frozen_string_literal: true

require "uri"

# Run inside the Canvas Rails container:
# docker exec -i canvas-lms-web-1 bundle exec rails runner - < scripts/setup_canvas_lti.rb

tool_name = ENV.fetch("DA_LTI_TOOL_NAME", "DA Platform Local")
tool_base_url = ENV.fetch("DA_LTI_TOOL_URL", "http://localhost:3001").sub(%r{/+$}, "")
tool_domain = URI.parse(tool_base_url).host
tool_jwks_url = ENV.fetch(
  "DA_LTI_JWKS_URL",
  "http://host.docker.internal:3001/.well-known/jwks.json"
)
# Every tool is deployed to the root account, so member tools show their own
# entries in each course. Tag their menu labels to tell them apart.
menu_suffix = ENV.fetch("DA_LTI_MENU_SUFFIX") do
  tool_name == "DA Platform Local" ? "" : " (#{tool_name.sub(/\ADA Platform\s*-\s*/, "")})"
end

account = Account.default
admin = account.active_account_users.preload(:user).filter_map(&:user).first
admin ||= User.active.first
raise "No active Canvas administrator/user found" unless admin

registration_params = {
  name: tool_name,
  admin_nickname: tool_name,
  description: "Local DA learning and content-generation platform",
  vendor: "252-DA",
  lock_deploying: true,
  workflow_state: "on"
}

configuration_params = {
  title: tool_name,
  description: "AI-assisted learning and content generation",
  target_link_uri: "#{tool_base_url}/",
  oidc_initiation_url: "#{tool_base_url}/lti/login",
  redirect_uris: ["#{tool_base_url}/lti/launch"],
  public_jwk_url: tool_jwks_url,
  scopes: [
    "https://purl.imsglobal.org/spec/lti-ags/scope/lineitem",
    "https://purl.imsglobal.org/spec/lti-ags/scope/result.readonly",
    "https://purl.imsglobal.org/spec/lti-ags/scope/score",
    # Asset Processor (Document Processor): nhận thông báo bài nộp, tải file,
    # gửi báo cáo chấm về SpeedGrader. Xem docs/essay-asset-processor.md.
    "https://purl.imsglobal.org/spec/lti/scope/noticehandlers",
    "https://purl.imsglobal.org/spec/lti/scope/asset.readonly",
    "https://purl.imsglobal.org/spec/lti/scope/report",
    # NRPS: đọc danh sách lớp để biết cả sinh viên chưa từng mở DA
    # (core-api RosterSyncService). Xem docs/canvas_lti_setup.md.
    "https://purl.imsglobal.org/spec/lti-nrps/scope/contextmembership.readonly"
  ],
  domain: tool_domain,
  tool_id: "da-platform-local",
  privacy_level: "public",
  # Biến Canvas được mở rộng thành giá trị thật ở mỗi launch và đi trong claim
  # .../lti/claim/custom. Biến không có ngữ cảnh (ví dụ $Canvas.assignment.* khi
  # mở từ menu khóa học) được Canvas để nguyên chuỗi "$Canvas...", nên phía
  # nhận phải coi chuỗi bắt đầu bằng "$" là không có giá trị.
  # $Canvas.module.id / moduleItem.id chỉ có khi launch từ một module item, không
  # có ở launch Deep Linking của module_menu_modal.
  custom_fields: {
    canvas_course_id: "$Canvas.course.id",
    canvas_user_id: "$Canvas.user.id",
    canvas_module_id: "$Canvas.module.id",
    canvas_module_item_id: "$Canvas.moduleItem.id",
    canvas_assignment_id: "$Canvas.assignment.id",
    assignment_points: "$Canvas.assignment.pointsPossible",
    assignment_due: "$Canvas.assignment.dueAt.iso8601",
    assignment_unlock: "$Canvas.assignment.unlockAt.iso8601",
    assignment_lock: "$Canvas.assignment.lockAt.iso8601",
    assignment_attempts: "$Canvas.assignment.allowedAttempts",
    assignment_published: "$Canvas.assignment.published"
  },
  launch_settings: {
    text: "DA Platform#{menu_suffix}",
    display_type: "full_width_in_context"
  },
  placements: [
    {
      placement: "course_navigation",
      enabled: true,
      message_type: "LtiResourceLinkRequest",
      text: "DA Platform#{menu_suffix}",
      target_link_uri: "#{tool_base_url}/"
    },
    {
      # Nút chat ở thanh trên của Canvas, mở thành ngăn bên ở mọi trang. Cần cờ
      # top_navigation_placement của root account. custom_fields đi trong id_token
      # đã ký; launch route đọc target_kind=chat để vào thẳng trang chat của khóa
      # học đang mở (không có khóa học thì báo rõ).
      # Công cụ được ghim chỉ hiện icon (16x16), không có chữ; thiếu icon_url thì
      # Canvas tự vẽ một ô chữ cái khó nhận ra. Tên ở đây là tiêu đề ngăn bên.
      placement: "top_navigation",
      enabled: true,
      message_type: "LtiResourceLinkRequest",
      text: "Trợ giảng AI#{menu_suffix}",
      icon_url: "#{tool_base_url}/icons/tro-giang-ai.svg",
      target_link_uri: "#{tool_base_url}/",
      custom_fields: { target_kind: "chat" }
    },
    {
      placement: "module_menu_modal",
      enabled: true,
      message_type: "LtiDeepLinkingRequest",
      text: "Sinh quiz bằng DA#{menu_suffix}",
      target_link_uri: "#{tool_base_url}/lti/deep-link",
      selection_width: 1100,
      selection_height: 800
    },
    {
      # Nút "Add Document Processing App" trên trang sửa Assignment nộp file.
      placement: "ActivityAssetProcessor",
      enabled: true,
      message_type: "LtiDeepLinkingRequest",
      text: "Chấm bài luận bằng AI (DA)#{menu_suffix}",
      target_link_uri: "#{tool_base_url}/lti/asset-processor"
    }
  ]
}.with_indifferent_access

registration = Lti::Registration.active.find_by(account: account, name: tool_name)
action = registration ? "updated" : "created"

if registration
  # Preserve existing placements/claims managed elsewhere when adding the
  # module menu. Updating the registration must retain its client/deployment.
  existing_configuration = registration.internal_lti_configuration&.as_json
  if existing_configuration.is_a?(Hash)
    existing_configuration = existing_configuration.with_indifferent_access
    wanted_placements = configuration_params[:placements].map { |p| p[:placement] }
    configuration_params[:placements] += Array(existing_configuration[:placements]).reject { |p| wanted_placements.include?(p["placement"] || p[:placement]) }
    # Giữ custom field đã có từ nơi khác, nhưng giá trị khai báo ở đây thắng.
    configuration_params[:custom_fields] = (existing_configuration[:custom_fields] || {}).to_h.merge(configuration_params[:custom_fields])
    configuration_params[:scopes] |= Array(existing_configuration[:scopes])
  end
  registration = Lti::UpdateRegistrationService.call(
    id: registration.id,
    account: account,
    updated_by: admin,
    registration_params: registration_params,
    configuration_params: configuration_params,
    comment: "Synced by da-platform/scripts/setup_canvas_lti.rb"
  )
else
  registration = Lti::CreateRegistrationService.call(
    account: account,
    created_by: admin,
    registration_params: registration_params,
    configuration_params: configuration_params
  )
end

deployment = registration.deployments.active.find_by(context: account)
deployment ||= registration.new_external_tool(
  account,
  current_user: admin,
  available: true,
  enabled: true
)

deployment.update!(workflow_state: registration.privacy_level) if deployment.workflow_state == "disabled"

control = Lti::ContextControl.active.find_by(
  deployment: deployment,
  account: account,
  course_id: nil
)
control&.update!(available: true, updated_by: admin)

puts({
  action: action,
  account_id: account.id,
  registration_id: registration.id,
  developer_key_id: registration.developer_key.id,
  client_id: deployment.global_developer_key_id.to_s,
  deployment_id: deployment.deployment_id,
  available: control&.available,
  oidc_login_url: configuration_params[:oidc_initiation_url],
  redirect_uri: configuration_params[:redirect_uris].first
}.to_json)
