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
    "https://purl.imsglobal.org/spec/lti-ags/scope/score"
  ],
  domain: tool_domain,
  tool_id: "da-platform-local",
  privacy_level: "public",
  custom_fields: {},
  launch_settings: {
    text: "DA Platform",
    display_type: "full_width_in_context"
  },
  placements: [
    {
      placement: "course_navigation",
      enabled: true,
      message_type: "LtiResourceLinkRequest",
      text: "DA Platform",
      target_link_uri: "#{tool_base_url}/"
    },
    {
      placement: "module_menu_modal",
      enabled: true,
      message_type: "LtiDeepLinkingRequest",
      text: "Sinh quiz bằng DA",
      target_link_uri: "#{tool_base_url}/lti/deep-link",
      selection_width: 1100,
      selection_height: 800
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
    configuration_params[:custom_fields] = existing_configuration[:custom_fields] || {}
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
